from __future__ import annotations

import json
from hashlib import sha256
import re
from typing import Any, Optional

import httpx

from backend.core.text import normalize_text


_STYLE_VARIANTS: tuple[str, ...] = (
    "thân thiện, gần gũi",
    "ngắn gọn, rõ ý",
    "tư vấn chuyên nghiệp, tự nhiên",
)


_MAX_GROUNDING_ITEMS = 8
_MAX_GROUNDING_CHARS = 240
_MAX_REWRITE_SENTENCES = 2
_MAX_REWRITE_TOKENS = 90
_MAX_REWRITE_WORDS = 60
_MAX_REWRITE_WORDS_BY_INTENT: dict[str, int] = {
    "available_products": 180,
    "order_support": 90,
}


_BOILERPLATE_PREFIXES: tuple[str, ...] = (
    "Mình cập nhật nhanh cho bạn nè:",
    "Mình tóm tắt gọn theo nhu cầu của bạn:",
    "Mình xem lại dữ liệu và đề xuất thế này:",
    "Mình lọc nhanh theo nhu cầu của bạn và thấy vài lựa chọn khá hợp nè.",
    "Mình vừa so khớp theo khẩu vị bạn mô tả, kết quả khá ổn.",
    "Dựa trên tiêu chí bạn đưa, mình chọn được những trái cây phù hợp nhất lúc này.",
    "Mình vừa rà nhanh các mặt hàng đang có và chọn ra nhóm dễ ăn nhất.",
    "Shop đang có vài lựa chọn ngon khá rõ theo tiêu chí bạn hỏi.",
    "Mình lọc nhanh danh sách hôm nay và thấy các lựa chọn sau khá ổn.",
)


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


def _trim_sentences(value: str, *, max_sentences: int = _MAX_REWRITE_SENTENCES) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return cleaned

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    if len(sentences) <= max_sentences:
        return cleaned
    return _clean_text(" ".join(sentences[:max_sentences]))


def _strip_boilerplate_prefixes(value: str) -> str:
    cleaned = _clean_text(value)
    for prefix in _BOILERPLATE_PREFIXES:
        cleaned = re.sub(rf"^{re.escape(prefix)}\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _trim_words(value: str, *, max_words: int = _MAX_REWRITE_WORDS) -> str:
    cleaned = _clean_text(value)
    words = cleaned.split()
    if len(words) <= max_words:
        return cleaned

    trimmed = " ".join(words[:max_words]).rstrip(" ,;:")
    if trimmed and trimmed[-1] not in ".!?":
        trimmed += "."
    return trimmed


def _strip_soft_follow_up(value: str) -> str:
    cleaned = _clean_text(value)
    trailing_follow_up = (
        r"\s+(?:Nếu muốn|Nếu cần|Bạn muốn|Bạn thích|Bạn có muốn|Mình có thể|Mình sẽ)"
        r"[^.?!]*[.?!]?$"
    )
    for _ in range(2):
        shortened = re.sub(trailing_follow_up, "", cleaned, flags=re.IGNORECASE).strip()
        if shortened == cleaned:
            return cleaned
        cleaned = shortened
    return cleaned


def _finalize_concise_answer(
    value: str,
    *,
    allow_follow_up: bool = True,
    max_words: int = _MAX_REWRITE_WORDS,
) -> str:
    cleaned = _strip_boilerplate_prefixes(value)
    if not allow_follow_up:
        cleaned = _strip_soft_follow_up(cleaned)
    cleaned = _trim_sentences(cleaned)
    return _trim_words(cleaned, max_words=max_words)


class ResponseRewriter:
    def __init__(
        self,
        *,
        lm_studio_base_url: str = "http://localhost:1234/v1",
        lm_studio_model_name: str = "",
        lm_studio_timeout_seconds: float = 15.0,
        lm_studio_temperature: float = 0.2,
    ) -> None:
        self.lm_studio_base_url = lm_studio_base_url.rstrip("/")
        self.lm_studio_model_name = lm_studio_model_name.strip()
        self.lm_studio_timeout_seconds = lm_studio_timeout_seconds
        self.lm_studio_temperature = lm_studio_temperature
        self._last_lm_studio_error = ""
        self._autodetected_lm_studio_model_name = ""

    def rewrite(
        self,
        *,
        base_answer: str,
        user_message: str,
        intent: str,
        session_id: str,
        allow_follow_up: bool = True,
        rag_context: Optional[list[str]] = None,
    ) -> tuple[str, str]:
        cleaned = _clean_text(base_answer)
        if not cleaned:
            return base_answer, "none"

        grounding_context = self._prepare_grounding_context(rag_context)

        if not self._can_use_lm_studio():
            raise RuntimeError(
                "Pipeline LM Studio chưa sẵn sàng. "
                "Hãy kiểm tra LM_STUDIO_BASE_URL và load một model chat trong LM Studio."
            )

        lm_answer = self._rewrite_with_lm_studio(
            base_answer=cleaned,
            user_message=user_message,
            intent=intent,
            session_id=session_id,
            allow_follow_up=allow_follow_up,
            rag_context=grounding_context,
        )
        if not lm_answer:
            detail = self._last_lm_studio_error or "LM Studio không trả về nội dung hợp lệ."
            raise RuntimeError(detail)

        return lm_answer, "lm_studio"

    def resolve_delivery_area(
        self,
        *,
        query: str,
        allowed_areas: tuple[str, ...],
    ) -> Optional[dict[str, Any]]:
        if not allowed_areas or not self._can_use_lm_studio():
            return None

        allowed_area_block = "\n".join(f"- {area}" for area in allowed_areas)
        prompt = (
            "Bạn là bộ phân tích địa chỉ giao hàng nội thành Hà Nội cho shop xuất phát từ Nam Từ Liêm.\n"
            "Nhiệm vụ: đọc tin nhắn khách và xác định địa chỉ/phố/đường/ngõ thuộc đúng một khu vực trong danh sách cho phép.\n"
            "Danh sách khu vực cho phép:\n"
            f"{allowed_area_block}\n\n"
            "Quy tắc bắt buộc:\n"
            "- Chỉ chọn area nằm trong danh sách cho phép; không tự tạo tên khu vực khác.\n"
            "- Dùng hiểu biết địa lý phổ biến ở Hà Nội để suy luận phố, đường, ngõ, tòa nhà hoặc khu đô thị.\n"
            "- Nếu tên đường có thể thuộc nhiều khu vực hoặc không đủ chắc chắn, đặt area=null và confidence <= 0.5.\n"
            "- Không tính thời gian giao hàng; chỉ phân loại khu vực.\n"
            "- Trả về JSON thuần theo schema: "
            "{\"area\":string|null,\"confidence\":0-1,\"matched_text\":string,\"reason\":string}.\n\n"
            "Ví dụ:\n"
            "Tin: ship tới ngõ 15 Duy Tân -> {\"area\":\"Cầu Giấy\",\"confidence\":0.86,\"matched_text\":\"ngõ 15 Duy Tân\",\"reason\":\"Duy Tân thuộc khu Cầu Giấy\"}\n"
            "Tin: giao phố Quan Nhân -> {\"area\":\"Thanh Xuân\",\"confidence\":0.82,\"matched_text\":\"phố Quan Nhân\",\"reason\":\"Quan Nhân thường thuộc Thanh Xuân\"}\n"
            "Tin: giao Nguyễn Trãi -> {\"area\":null,\"confidence\":0.4,\"matched_text\":\"Nguyễn Trãi\",\"reason\":\"Nguyễn Trãi kéo dài qua nhiều khu vực\"}\n\n"
            f"Tin nhắn khách: {query}"
        )

        raw = self._call_lm_studio(prompt=prompt, max_tokens=220)
        if not raw:
            return None

        parsed = self._parse_json_payload(raw)
        if not parsed:
            parsed = self._parse_json_payload(self._normalize_json_like(raw))
        if not parsed:
            return None

        area = parsed.get("area")
        if not isinstance(area, str) or not area.strip():
            return None

        normalized_allowed = {normalize_text(area_name): area_name for area_name in allowed_areas}
        canonical_area = normalized_allowed.get(normalize_text(area))
        if not canonical_area:
            return None

        try:
            confidence = float(parsed.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < 0.65:
            return None

        matched_text = parsed.get("matched_text")
        reason = parsed.get("reason")
        return {
            "area": canonical_area,
            "confidence": confidence,
            "matched_text": matched_text.strip() if isinstance(matched_text, str) else "",
            "reason": reason.strip() if isinstance(reason, str) else "",
            "provider": "lm_studio",
        }

    def _can_use_lm_studio(self) -> bool:
        return bool(self.lm_studio_base_url)

    def _prepare_grounding_context(self, rag_context: Optional[list[str]]) -> list[str]:
        if not rag_context:
            return []

        normalized_seen: set[str] = set()
        sanitized: list[str] = []
        for item in rag_context:
            line = _clean_text(str(item))
            if not line:
                continue

            if len(line) > _MAX_GROUNDING_CHARS:
                line = line[:_MAX_GROUNDING_CHARS].rstrip() + "..."

            key = normalize_text(line)
            if key in normalized_seen:
                continue

            normalized_seen.add(key)
            sanitized.append(line)
            if len(sanitized) >= _MAX_GROUNDING_ITEMS:
                break

        return sanitized

    @staticmethod
    def _build_grounding_block(rag_context: list[str]) -> str:
        if not rag_context:
            return "Nguồn dữ kiện truy hồi (RAG): không có thêm dữ liệu ngoài bản nháp hiện tại."

        bullets = "\n".join(f"- {item}" for item in rag_context)
        return f"Nguồn dữ kiện truy hồi (RAG):\n{bullets}"

    @staticmethod
    def _build_rewrite_prompt(
        *,
        base_answer: str,
        user_message: str,
        intent: str,
        tone: str,
        allow_follow_up: bool,
        grounding_block: str,
    ) -> str:
        follow_up_rule = (
            "Chỉ thêm câu hỏi gợi mở khi người dùng đang chọn mua và câu hỏi đó giúp chốt thông tin còn thiếu."
            if allow_follow_up
            else "Không thêm câu hỏi gợi mở ở cuối."
        )

        return (
            "Bạn là chatbot tư vấn bán trái cây trên Facebook Messenger.\n"
            "Nhiệm vụ: viết lại bản nháp thành câu trả lời cuối cùng bằng tiếng Việt có dấu.\n"
            "Ưu tiên bắt buộc theo thứ tự:\n"
            "1. Đúng dữ kiện: chỉ dùng bản nháp và nguồn RAG; không bịa tên sản phẩm, giá, tồn kho, mức vị, chính sách hoặc khuyến mãi.\n"
            "2. Trả lời trực tiếp câu hỏi ngay ở câu đầu; nếu người dùng hỏi giá/tồn kho thì nêu giá/tồn kho trước.\n"
            "3. Ngắn gọn nhất có thể: tối đa 2 câu và khoảng 45 từ; không mở bài, không giải thích quy trình, không nêu điểm phù hợp.\n"
            "4. Không dùng các câu đệm kiểu 'Mình tóm tắt', 'Mình vừa so khớp', 'Mình xem lại dữ liệu', 'theo nhu cầu của bạn'.\n"
            "5. Nếu người dùng hỏi một sản phẩm cụ thể, chỉ trả lời sản phẩm đó; không tự thêm sản phẩm thay thế nếu người dùng không hỏi.\n"
            "6. Giọng thân thiện như nhân viên shop trái cây; xưng mình/bạn; không emoji, không markdown, không hashtag.\n"
            "7. Nếu thiếu dữ kiện hoặc không chắc, nói rõ là mình chưa có thông tin thay vì đoán.\n"
            f"Phong cách nhỏ: {tone}. {follow_up_rule}\n\n"
            f"Intent: {intent}\n"
            f"Câu hỏi người dùng: {user_message}\n"
            f"{grounding_block}\n"
            f"Bản nháp hiện tại: {base_answer}\n\n"
            "Chỉ trả về câu trả lời cuối cùng, không giải thích."
        )

    def _lm_studio_chat_urls(self) -> list[str]:
        base = self.lm_studio_base_url.rstrip("/")
        urls = [f"{base}/chat/completions"]
        if not base.endswith("/v1"):
            urls.append(f"{base}/v1/chat/completions")
        return urls

    def _lm_studio_models_url(self) -> str:
        base = self.lm_studio_base_url.rstrip("/")
        return f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"

    @staticmethod
    def _is_embedding_model_name(model_name: str) -> bool:
        name = model_name.strip().lower()
        if not name:
            return False

        embedding_markers = (
            "embed",
            "embedding",
            "bge",
            "e5",
            "nomic-embed",
            "gte",
        )
        return any(marker in name for marker in embedding_markers)

    def _fetch_lm_studio_model_ids(self) -> list[str]:
        url = self._lm_studio_models_url()
        timeout = max(3.0, min(self.lm_studio_timeout_seconds, 8.0))

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []

        if not isinstance(payload, dict):
            return []

        data = payload.get("data")
        if not isinstance(data, list):
            return []

        model_ids: list[str] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id.strip():
                model_ids.append(model_id.strip())

        return model_ids

    @staticmethod
    def _extract_text_from_lm_payload(payload: dict[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = payload.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for chunk in content:
                    if not isinstance(chunk, dict):
                        continue
                    text = chunk.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            if parts:
                return " ".join(parts)

        return ""

    def _call_lm_studio(self, *, prompt: str, max_tokens: int = _MAX_REWRITE_TOKENS) -> Optional[str]:
        if not self._can_use_lm_studio():
            return None

        self._last_lm_studio_error = ""

        payload: dict = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.lm_studio_temperature,
            "max_tokens": max_tokens,
        }

        model_name = self.lm_studio_model_name or self._autodetected_lm_studio_model_name
        if not model_name:
            model_ids = self._fetch_lm_studio_model_ids()
            if model_ids:
                chat_candidates = [name for name in model_ids if not self._is_embedding_model_name(name)]
                if chat_candidates:
                    model_name = chat_candidates[0]
                    self._autodetected_lm_studio_model_name = model_name
                else:
                    listed = ", ".join(model_ids[:5])
                    self._last_lm_studio_error = (
                        "LM Studio hiện chỉ có model embedding, chưa có model chat để gọi /chat/completions. "
                        f"Models hiện tại: {listed}. Hãy load một model chat/instruct trong LM Studio."
                    )
                    return None

        if model_name:
            payload["model"] = model_name

        urls = self._lm_studio_chat_urls()
        for idx, url in enumerate(urls):
            try:
                with httpx.Client(timeout=self.lm_studio_timeout_seconds) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()

                if not isinstance(data, dict):
                    self._last_lm_studio_error = (
                        f"LM Studio trả payload không hợp lệ tại {url}. "
                        "Hãy kiểm tra gateway/proxy trả đúng JSON object."
                    )
                    continue

                error_payload = data.get("error")
                if error_payload:
                    if isinstance(error_payload, dict):
                        error_text = str(error_payload.get("message") or error_payload)
                    else:
                        error_text = str(error_payload)

                    self._last_lm_studio_error = f"LM Studio trả lỗi tại {url}: {error_text}"
                    if idx < len(urls) - 1 and "Unexpected endpoint or method" in error_text:
                        continue
                    return None

                choices = data.get("choices")
                if isinstance(choices, list) and choices:
                    first_choice = choices[0]
                    message = first_choice.get("message") if isinstance(first_choice, dict) else None
                    text = ""

                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str):
                            text = content.strip()
                        elif isinstance(content, list):
                            text_parts: list[str] = []
                            for item in content:
                                if not isinstance(item, dict):
                                    continue
                                if isinstance(item.get("text"), str):
                                    text_parts.append(item["text"].strip())
                            text = " ".join(part for part in text_parts if part)

                        if not text:
                            reasoning_content = message.get("reasoning_content") or message.get("reasoning") or ""
                            if isinstance(reasoning_content, str):
                                text = self._extract_from_reasoning(reasoning_content)

                    if not text and isinstance(first_choice, dict):
                        choice_text = first_choice.get("text")
                        if isinstance(choice_text, str):
                            text = choice_text.strip()

                    text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                    if text:
                        return text

                alt_text = self._extract_text_from_lm_payload(data)
                alt_text = alt_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                if alt_text:
                    return alt_text

                self._last_lm_studio_error = (
                    "LM Studio trả payload không có choices/output_text hợp lệ. "
                    f"URL: {url}. Keys: {', '.join(sorted(data.keys()))[:180]}"
                )
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else "unknown"
                body = ""
                if exc.response is not None:
                    body = (exc.response.text or "").strip()[:500]
                self._last_lm_studio_error = (
                    f"LM Studio trả lỗi HTTP {status}. "
                    f"URL: {url}. Body: {body or 'không có nội dung'}"
                )
                if idx < len(urls) - 1 and status in {404, 405}:
                    continue
            except httpx.TimeoutException:
                self._last_lm_studio_error = (
                    f"Không kết nối được LM Studio (timeout) tại {url}. "
                    "Hãy kiểm tra server LM Studio đang chạy và mạng có thể truy cập."
                )
            except httpx.ConnectError as exc:
                self._last_lm_studio_error = (
                    f"Không kết nối được LM Studio tại {url}: {exc}. "
                    "Hãy kiểm tra host/port và bật Local Server trong LM Studio."
                )
            except Exception as exc:
                self._last_lm_studio_error = f"LM Studio lỗi không xác định: {type(exc).__name__}: {exc}"

        return None

    @staticmethod
    def _extract_from_reasoning(reasoning: str) -> str:
        if not reasoning:
            return ""

        separators = [
            # Vietnamese
            "---", "Kết luận", "Kết Luận", "KẾT LUẬN", "## Kết", "**Kết",
            # English (reasoning models often conclude in English)
            "Final answer", "Final Answer", "FINAL ANSWER",
            "In conclusion", "In summary", "Therefore,", "So,",
            "The answer is", "My response:", "Response:",
        ]
        last_pos = -1
        last_sep = ""
        for sep in separators:
            pos = reasoning.rfind(sep)
            if pos > last_pos:
                last_pos = pos
                last_sep = sep

        if last_pos != -1:
            after = reasoning[last_pos + len(last_sep):].strip().lstrip(":").strip()
            if after:
                for line in after.splitlines():
                    line = line.strip().lstrip("#").lstrip("*").strip()
                    if line and len(line) > 5:
                        return line

        # Fallback: lấy dòng cuối cùng có nội dung
        for line in reversed(reasoning.splitlines()):
            line = line.strip().lstrip("#").lstrip("*").strip()
            if line and len(line) > 5:
                return line

        return ""

    def _rewrite_with_lm_studio(
        self,
        *,
        base_answer: str,
        user_message: str,
        intent: str,
        session_id: str,
        allow_follow_up: bool,
        rag_context: list[str],
    ) -> Optional[str]:
        style_idx = self._style_index(user_message=user_message, intent=intent, session_id=session_id)
        tone = _STYLE_VARIANTS[style_idx]
        grounding_block = self._build_grounding_block(rag_context)

        prompt = self._build_rewrite_prompt(
            base_answer=base_answer,
            user_message=user_message,
            intent=intent,
            tone=tone,
            allow_follow_up=allow_follow_up,
            grounding_block=grounding_block,
        )

        generated = self._call_lm_studio(prompt=prompt)
        if not generated:
            return None
        generated = re.sub(r"[#*`]+", "", generated)
        generated = re.sub(r"^(Câu trả lời|Trả lời|Answer|Response)\s*:\s*", "", generated.strip(), flags=re.IGNORECASE)
        return _finalize_concise_answer(
            generated,
            allow_follow_up=allow_follow_up,
            max_words=_MAX_REWRITE_WORDS_BY_INTENT.get(intent, _MAX_REWRITE_WORDS),
        )

    def _style_index(self, *, user_message: str, intent: str, session_id: str) -> int:
        seed = f"{session_id}|{intent}|{normalize_text(user_message)}"
        digest = sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % len(_STYLE_VARIANTS)

    @staticmethod
    def _parse_json_payload(text: str) -> Optional[dict[str, Any]]:
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = candidate.strip("`")
            candidate = candidate.replace("json", "", 1).strip()

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        candidate = candidate[start : end + 1]
        try:
            payload = json.loads(candidate)
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None
        return payload

    @staticmethod
    def _normalize_json_like(text: str) -> str:
        candidate = text.strip()
        if not candidate:
            return candidate

        if candidate.startswith("```"):
            candidate = candidate.strip("`")
            candidate = candidate.replace("json", "", 1).strip()

        candidate = candidate.replace("\r\n", "\n").replace("\r", "\n")

        # Common model variants: Python-like booleans/None and trailing commas.
        candidate = re.sub(r"\bTrue\b", "true", candidate)
        candidate = re.sub(r"\bFalse\b", "false", candidate)
        candidate = re.sub(r"\bNone\b", "null", candidate)

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)

        # Best-effort conversion for single-quoted dict-like outputs.
        if "'" in candidate and '"' not in candidate:
            candidate = candidate.replace("'", '"')

        return candidate
