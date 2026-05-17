from __future__ import annotations

from hashlib import sha256
from typing import Optional

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


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


class ResponseRewriter:
    def __init__(
        self,
        *,
        llm_enabled: bool = True,
        gemini_api_key: str = "",
        gemini_model_name: str = "gemini-1.5-flash",
        gemini_timeout_seconds: float = 6.0,
        gemini_temperature: float = 0.2,
    ) -> None:
        self.llm_enabled = llm_enabled
        self.gemini_api_key = gemini_api_key.strip()
        self.gemini_model_name = gemini_model_name
        self.gemini_timeout_seconds = gemini_timeout_seconds
        self.gemini_temperature = gemini_temperature

    def rewrite(
        self,
        *,
        base_answer: str,
        user_message: str,
        intent: str,
        session_id: str,
        language: str = "vi",
        allow_follow_up: bool = True,
    ) -> tuple[str, str]:
        cleaned = _clean_text(base_answer)
        if not cleaned:
            return base_answer, "none"

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
            )
            if llm_answer:
                return llm_answer, "gemini"

        return deterministic_answer, "deterministic"

    def _can_use_gemini(self) -> bool:
        return self.llm_enabled and bool(self.gemini_api_key)

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
    ) -> Optional[str]:
        style_idx = self._style_index(user_message=user_message, intent=intent, session_id=session_id)
        tone = _STYLE_VARIANTS[style_idx]["tone"]

        follow_up_rule = (
            "Có thể kết câu bằng 1 câu gợi mở ngắn."
            if allow_follow_up
            else "Không thêm câu hỏi gợi mở ở cuối."
        )

        prompt = (
            "Bạn là trợ lý tư vấn trái cây. Hãy viết lại câu trả lời tiếng Việt cho tự nhiên hơn, "
            "nhưng phải giữ nguyên dữ kiện thực tế (tên sản phẩm, giá, số lượng, mức độ). "
            "Không bịa thông tin mới, không đổi nghĩa, không dùng markdown. "
            f"Giữ giọng điệu: {tone}. {follow_up_rule} "
            "Độ dài 2-4 câu, dễ đọc.\n\n"
            f"Intent: {intent}\n"
            f"Câu hỏi người dùng: {user_message}\n"
            f"Bản nháp hiện tại: {base_answer}\n\n"
            "Trả về duy nhất câu trả lời đã viết lại."
        )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.gemini_temperature,
                "topP": 0.9,
                "maxOutputTokens": 280,
            },
        }
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

        return _clean_text(generated)

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