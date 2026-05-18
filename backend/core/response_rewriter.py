from __future__ import annotations

import json
from hashlib import sha256
import re
from typing import Any, Optional

import httpx

from backend.core.text import normalize_text


_STYLE_VARIANTS: tuple[dict[str, str], ...] = (
    {
        "lead": "Mình cập nhật nhanh cho bạn nè:",
        "tone": "thân thiện, gần gũi",
    },
    {
        "lead": "Mình tóm tắt gọn theo nhu cầu của bạn:",
        "tone": "ngắn gọn, rõ ý",
    },
    {
        "lead": "Mình xem lại dữ liệu và đề xuất thế này:",
        "tone": "tư vấn chuyên nghiệp, tự nhiên",
    },
)


_FOLLOW_UPS_BY_INTENT: dict[str, tuple[str, ...]] = {
    "available_products": (
        "Bạn muốn mình lọc tiếp theo vị ngọt, độ chua hay ngân sách?",
        "Nếu cần, mình sẽ thu hẹp thêm theo mục đích ăn tươi hay ép nước.",
        "Bạn thích mình chốt nhanh 1-2 lựa chọn dễ mua nhất không?",
    ),
    "recommendation": (
        "Mình có thể tinh chỉnh thêm theo tiêu chí bạn ưu tiên nhất.",
        "Nếu muốn, mình sẽ lọc thêm phương án tiết kiệm hơn.",
        "Bạn muốn mình đẩy mạnh theo hướng ngọt hơn hay ít chua hơn?",
    ),
    "inventory_check": (
        "Bạn muốn mình gợi ý thêm sản phẩm cùng nhóm vị không?",
        "Nếu cần, mình sẽ kiểm tra thêm vài lựa chọn tương tự đang còn hàng.",
        "Mình có thể đề xuất thêm lựa chọn thay thế nếu bạn muốn.",
    ),
    "faq_shipping": (
        "Bạn muốn mình ước tính luôn khung giờ giao theo khu vực của bạn không?",
        "Nếu cần, mình sẽ nói rõ thêm phần phí theo địa chỉ giao.",
        "Mình có thể hướng dẫn luôn cách đặt để nhận nhanh nhất.",
    ),
    "faq_return": (
        "Bạn muốn mình tóm tắt luôn các bước đổi trả nhanh không?",
        "Nếu cần, mình sẽ ghi rõ giấy tờ/thông tin cần chuẩn bị.",
        "Mình có thể hướng dẫn bạn cách xử lý nhanh ngay trong chat.",
    ),
    "faq_storage": (
        "Nếu muốn, mình có thể gợi ý cách bảo quản riêng theo từng loại trái.",
        "Mình có thể tách thêm mẹo bảo quản cho tủ mát và nhiệt độ phòng.",
        "Bạn muốn mình viết checklist bảo quản ngắn gọn để dễ áp dụng không?",
    ),
    "out_of_domain": (
        "Bạn thử hỏi theo sản phẩm, vị, ngân sách hoặc tình trạng còn hàng nhé.",
        "Mình hỗ trợ tốt nhất ở mảng trái cây, tồn kho, giao hàng và đổi trả.",
        "Bạn gửi lại câu hỏi theo ngữ cảnh mua trái cây, mình hỗ trợ ngay.",
    ),
}

_MAX_GROUNDING_ITEMS = 8
_MAX_GROUNDING_CHARS = 240


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


class ResponseRewriter:
    def __init__(
        self,
        *,
        generation_mode: str = "llm_only",
        llm_enabled: bool = True,
        gemini_api_key: str = "",
        gemini_model_name: str = "gemini-1.5-flash",
        gemini_timeout_seconds: float = 6.0,
        gemini_temperature: float = 0.2,
        lm_studio_base_url: str = "http://localhost:1234/v1",
        lm_studio_model_name: str = "",
        lm_studio_timeout_seconds: float = 15.0,
        lm_studio_temperature: float = 0.2,
    ) -> None:
        self.generation_mode = generation_mode.strip().lower()
        self.llm_enabled = llm_enabled
        self.gemini_api_key = gemini_api_key.strip()
        self.gemini_model_name = gemini_model_name
        self.gemini_timeout_seconds = gemini_timeout_seconds
        self.gemini_temperature = gemini_temperature
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
        language: str = "vi",
        allow_follow_up: bool = True,
        rag_context: Optional[list[str]] = None,
    ) -> tuple[str, str]:
        cleaned = _clean_text(base_answer)
        if not cleaned:
            return base_answer, "none"

        grounding_context = self._prepare_grounding_context(rag_context)

        if self.generation_mode == "deterministic":
            deterministic_answer = self._rewrite_deterministic(
                base_answer=cleaned,
                user_message=user_message,
                intent=intent,
                session_id=session_id,
                allow_follow_up=allow_follow_up,
            )
            return deterministic_answer, "deterministic"

        if self.generation_mode == "lm_studio":
            if not self._can_use_lm_studio():
                raise RuntimeError(
                    "Chế độ lm_studio đang bật nhưng LM Studio chưa sẵn sàng. "
                    "Hãy kiểm tra LM_STUDIO_MODEL_NAME và server đang chạy tại LM_STUDIO_BASE_URL."
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

        if self.generation_mode == "llm_only":
            if self._can_use_lm_studio():
                lm_answer = self._rewrite_with_lm_studio(
                    base_answer=cleaned,
                    user_message=user_message,
                    intent=intent,
                    session_id=session_id,
                    allow_follow_up=allow_follow_up,
                    rag_context=grounding_context,
                )
                if lm_answer:
                    return lm_answer, "lm_studio_strict"

            if self._can_use_gemini() and language.lower().startswith("vi"):
                llm_answer = self._rewrite_with_llm(
                    base_answer=cleaned,
                    user_message=user_message,
                    intent=intent,
                    session_id=session_id,
                    allow_follow_up=allow_follow_up,
                    rag_context=grounding_context,
                )
                if llm_answer:
                    return llm_answer, "gemini_strict"

            if not self._can_use_lm_studio() and not self._can_use_gemini():
                raise RuntimeError(
                    "Chế độ LLM-only đang bật nhưng chưa có provider nào sẵn sàng. "
                    "Hãy cấu hình LM_STUDIO_MODEL_NAME hoặc GEMINI_API_KEY."
                )

            if self._last_lm_studio_error and not self._can_use_gemini():
                raise RuntimeError(self._last_lm_studio_error)

            raise RuntimeError(
                "Chế độ LLM-only đang bật nhưng LLM không trả về nội dung hợp lệ. "
                "Không áp dụng fallback theo yêu cầu hiện tại."
            )

        deterministic_answer = self._rewrite_deterministic(
            base_answer=cleaned,
            user_message=user_message,
            intent=intent,
            session_id=session_id,
            allow_follow_up=allow_follow_up,
        )

        if self._can_use_gemini() and language.lower().startswith("vi"):
            llm_answer = self._rewrite_with_llm(
                base_answer=deterministic_answer,
                user_message=user_message,
                intent=intent,
                session_id=session_id,
                allow_follow_up=allow_follow_up,
                rag_context=grounding_context,
            )
            if llm_answer:
                return llm_answer, "gemini"

        if self._can_use_lm_studio():
            lm_answer = self._rewrite_with_lm_studio(
                base_answer=deterministic_answer,
                user_message=user_message,
                intent=intent,
                session_id=session_id,
                allow_follow_up=allow_follow_up,
                rag_context=grounding_context,
            )
            if lm_answer:
                return lm_answer, "lm_studio"

        return deterministic_answer, "deterministic"

    def review_answer_quality(
        self,
        *,
        question: str,
        answer: str,
        intent: str,
    ) -> dict[str, Any]:
        if not self._can_use_gemini():
            return {
                "review_mode": "unavailable",
                "score": None,
                "is_reasonable": None,
                "strengths": [],
                "issues": ["Gemini chưa sẵn sàng để tự đánh giá."],
                "lessons": [],
            }

        prompt = (
            "Bạn là QA reviewer cho chatbot bán trái cây. "
            "Đánh giá câu trả lời theo mức độ đúng ý người dùng, không lặp, và rõ ràng. "
            "Trả về JSON thuần với schema: "
            "{\"score\":0-100,\"is_reasonable\":true/false,\"strengths\":[...],\"issues\":[...],\"lessons\":[...],\"suggested_fix\":\"...\"}. "
            "Không thêm văn bản ngoài JSON.\n\n"
            f"Intent: {intent}\n"
            f"Question: {question}\n"
            f"Answer: {answer}\n"
        )

        raw = self._call_gemini(prompt=prompt, max_output_tokens=420, json_response=True)
        if not raw:
            return {
                "review_mode": "error",
                "score": None,
                "is_reasonable": None,
                "strengths": [],
                "issues": ["Gemini không trả về review."],
                "lessons": [],
            }

        parsed = self._parse_json_payload(raw)
        if not parsed:
            parsed = self._parse_json_payload(self._normalize_json_like(raw))

        if not parsed:
            return {
                "review_mode": "error",
                "score": None,
                "is_reasonable": None,
                "strengths": [],
                "issues": ["Gemini review không đúng định dạng JSON."],
                "lessons": [],
            }

        score = parsed.get("score")
        try:
            score_value = int(score) if score is not None else None
        except Exception:
            score_value = None

        is_reasonable = parsed.get("is_reasonable")
        if not isinstance(is_reasonable, bool):
            is_reasonable = None

        def _as_list(value: Any) -> list[str]:
            if not isinstance(value, list):
                return []
            return [str(item).strip() for item in value if str(item).strip()]

        review = {
            "review_mode": "gemini",
            "score": score_value,
            "is_reasonable": is_reasonable,
            "strengths": _as_list(parsed.get("strengths")),
            "issues": _as_list(parsed.get("issues")),
            "lessons": _as_list(parsed.get("lessons")),
            "suggested_fix": str(parsed.get("suggested_fix", "")).strip(),
        }
        return review

    def _can_use_gemini(self) -> bool:
        return self.llm_enabled and bool(self.gemini_api_key)

    def _can_use_lm_studio(self, *, require_model_name: bool = False) -> bool:
        if not self.llm_enabled or not self.lm_studio_base_url:
            return False
        if require_model_name and not self.lm_studio_model_name:
            return False
        return True

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

    def _call_lm_studio(self, *, prompt: str) -> Optional[str]:
        if not self._can_use_lm_studio():
            return None

        self._last_lm_studio_error = ""

        payload: dict = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.lm_studio_temperature,
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
        tone = _STYLE_VARIANTS[style_idx]["tone"]
        grounding_block = self._build_grounding_block(rag_context)

        follow_up_rule = (
            "Có thể kết câu bằng 1 câu gợi mở ngắn."
            if allow_follow_up
            else "Không thêm câu hỏi gợi mở ở cuối."
        )

        prompt = (
            "Bạn là trợ lý tư vấn trái cây. Hãy viết lại câu trả lời tiếng Việt cho tự nhiên hơn, "
            "nhưng phải giữ nguyên dữ kiện thực tế (tên sản phẩm, giá, số lượng, mức độ). "
            "Không bịa thông tin mới, không đổi nghĩa, không dùng markdown. "
            "Chỉ dùng dữ kiện trong bản nháp và phần RAG bên dưới; nếu thiếu dữ kiện thì giữ nguyên thông tin hiện có. "
            f"Giữ giọng điệu: {tone}. {follow_up_rule} "
            "Loại bỏ câu lặp hoặc ý lặp, tối đa 3 câu, rõ ràng.\n\n"
            f"Intent: {intent}\n"
            f"Câu hỏi người dùng: {user_message}\n"
            f"{grounding_block}\n"
            f"Bản nháp hiện tại: {base_answer}\n\n"
            "Trả về duy nhất câu trả lời đã viết lại."
        )

        generated = self._call_lm_studio(prompt=prompt)
        if not generated:
            return None
        generated = re.sub(r"[#*`]+", "", generated)
        return _clean_text(generated)

    def _style_index(self, *, user_message: str, intent: str, session_id: str) -> int:
        seed = f"{session_id}|{intent}|{normalize_text(user_message)}"
        digest = sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % len(_STYLE_VARIANTS)

    def _rewrite_deterministic(
        self,
        *,
        base_answer: str,
        user_message: str,
        intent: str,
        session_id: str,
        allow_follow_up: bool,
    ) -> str:
        if intent == "admin_update_stock":
            return base_answer

        style_idx = self._style_index(user_message=user_message, intent=intent, session_id=session_id)
        lead = _STYLE_VARIANTS[style_idx]["lead"]

        rewritten = base_answer if base_answer.startswith(lead) else f"{lead} {base_answer}"

        follow_up = self._pick_follow_up(intent=intent, style_idx=style_idx, allow_follow_up=allow_follow_up)
        if follow_up and "?" not in rewritten:
            rewritten = f"{rewritten} {follow_up}"

        return _clean_text(rewritten)

    def _pick_follow_up(self, *, intent: str, style_idx: int, allow_follow_up: bool) -> str:
        if not allow_follow_up:
            return ""

        choices = _FOLLOW_UPS_BY_INTENT.get(intent)
        if not choices:
            return ""

        return choices[style_idx % len(choices)]

    def _rewrite_with_llm(
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
        tone = _STYLE_VARIANTS[style_idx]["tone"]
        grounding_block = self._build_grounding_block(rag_context)

        follow_up_rule = (
            "Có thể kết câu bằng 1 câu gợi mở ngắn."
            if allow_follow_up
            else "Không thêm câu hỏi gợi mở ở cuối."
        )

        prompt = (
            "Bạn là trợ lý tư vấn trái cây. Hãy viết lại câu trả lời tiếng Việt cho tự nhiên hơn, "
            "nhưng phải giữ nguyên dữ kiện thực tế (tên sản phẩm, giá, số lượng, mức độ). "
            "Không bịa thông tin mới, không đổi nghĩa, không dùng markdown. "
            "Chỉ dùng dữ kiện trong bản nháp và phần RAG bên dưới; nếu thiếu dữ kiện thì giữ nguyên thông tin hiện có. "
            f"Giữ giọng điệu: {tone}. {follow_up_rule} "
            "Loại bỏ câu lặp hoặc ý lặp, tối đa 3 câu, rõ ràng.\n\n"
            f"Intent: {intent}\n"
            f"Câu hỏi người dùng: {user_message}\n"
            f"{grounding_block}\n"
            f"Bản nháp hiện tại: {base_answer}\n\n"
            "Trả về duy nhất câu trả lời đã viết lại."
        )

        generated = self._call_gemini(prompt=prompt, max_output_tokens=280)
        if not generated:
            return None

        return _clean_text(generated)

    def _call_gemini(self, *, prompt: str, max_output_tokens: int, json_response: bool = False) -> Optional[str]:
        if not self._can_use_gemini():
            return None

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.gemini_temperature,
                "topP": 0.9,
                "maxOutputTokens": max_output_tokens,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        if json_response:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model_name}:generateContent?key={self.gemini_api_key}"
        )

        try:
            with httpx.Client(timeout=self.gemini_timeout_seconds) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None

        generated = self._extract_gemini_text(data)
        if not generated:
            return None

        return generated

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

        # Common Gemini variants: Python-like booleans/None and trailing commas.
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

    @staticmethod
    def _extract_gemini_text(payload: dict) -> Optional[str]:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            return None

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            content = candidate.get("content")
            if not isinstance(content, dict):
                continue

            parts = content.get("parts")
            if not isinstance(parts, list):
                continue

            for part in parts:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

        return None