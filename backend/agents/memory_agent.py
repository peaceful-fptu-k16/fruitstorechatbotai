from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import re
from typing import Optional

from backend.core.text import normalize_text


@dataclass
class PreferenceProfile:
    prefers_sweet: bool = False
    prefers_low_sour: bool = False
    prefers_low_seed: bool = False
    prefers_juicy: bool = False
    prefers_aromatic: bool = False
    prefers_crunchy: bool = False
    prefers_low_sugar: bool = False
    prefers_high_fiber: bool = False
    prefers_high_vitamin_c: bool = False
    preferred_texture: Optional[str] = None
    budget_hint: Optional[int] = None
    signals: list[str] = field(default_factory=list)


class MemoryAgent:
    def __init__(self) -> None:
        self._profiles: dict[str, PreferenceProfile] = defaultdict(PreferenceProfile)

    @staticmethod
    def _format_vnd(amount: int) -> str:
        return f"{amount:,.0f}".replace(",", ".") + "đ"

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _extract_budget(self, normalized_message: str) -> Optional[int]:
        matches = re.findall(r"(\d+)\s*(k|nghin|ngan|trieu)?", normalized_message)
        for number_text, suffix in matches:
            value = int(number_text)
            if suffix in {"k", "nghin", "ngan"}:
                value *= 1000
            elif suffix == "trieu":
                value *= 1_000_000

            if value >= 1000:
                return value
        return None

    def update_from_message(self, session_id: str, message: str) -> None:
        profile = self._profiles[session_id]
        normalized = normalize_text(message)

        explicit_low_sweet = self._contains_any(
            normalized,
            (
                "khong qua ngot",
                "dung ngot qua",
                "it ngot",
                "ngot nhe",
                "ngot vua",
            ),
        )

        if "ngot" in normalized and not explicit_low_sweet:
            profile.prefers_sweet = True
            profile.signals.append("sweet")

        if (
            "it chua" in normalized
            or "khong chua" in normalized
            or "dung chua qua" in normalized
            or "chua nhe" in normalized
            or "khong qua chua" in normalized
        ):
            profile.prefers_low_sour = True
            profile.signals.append("low_sour")

        if "it hat" in normalized:
            profile.prefers_low_seed = True
            profile.signals.append("low_seed")

        if self._contains_any(normalized, ("mong nuoc", "nhieu nuoc", "ep nuoc", "giai nhiet")):
            profile.prefers_juicy = True
            profile.signals.append("juicy")

        if self._contains_any(normalized, ("thom", "mui thom")):
            profile.prefers_aromatic = True
            profile.signals.append("aromatic")

        if self._contains_any(normalized, ("gion", "gion rum", "do gion")):
            profile.prefers_crunchy = True
            profile.preferred_texture = "giòn"
            profile.signals.append("crunchy")

        if self._contains_any(normalized, ("it duong", "an kieng", "giam can", "keto")):
            profile.prefers_low_sugar = True
            profile.signals.append("low_sugar")

        if self._contains_any(normalized, ("chat xo", "tieu hoa", "no lau")):
            profile.prefers_high_fiber = True
            profile.signals.append("high_fiber")

        if self._contains_any(normalized, ("vitamin c", "de khang", "dep da")):
            profile.prefers_high_vitamin_c = True
            profile.signals.append("high_vitamin_c")

        if profile.preferred_texture is None and self._contains_any(normalized, ("mem", "de an", "de nhai")):
            profile.preferred_texture = "mềm"

        budget = self._extract_budget(normalized)
        if budget is not None:
            profile.budget_hint = budget

    def get_profile(self, session_id: str) -> PreferenceProfile:
        return self._profiles[session_id]

    def profile_context(self, session_id: str) -> str:
        profile = self.get_profile(session_id)
        hints = []
        if profile.prefers_sweet:
            hints.append("thích độ ngọt cao")
        if profile.prefers_low_sour:
            hints.append("ưu tiên vị ít chua")
        if profile.prefers_low_seed:
            hints.append("ưu tiên ít hạt")
        if profile.prefers_juicy:
            hints.append("thích trái mọng nước")
        if profile.prefers_aromatic:
            hints.append("ưu tiên trái thơm")
        if profile.prefers_crunchy:
            hints.append("thích kết cấu giòn")
        if profile.prefers_low_sugar:
            hints.append("ưu tiên ít đường")
        if profile.prefers_high_fiber:
            hints.append("ưu tiên nhiều chất xơ")
        if profile.prefers_high_vitamin_c:
            hints.append("ưu tiên trái giàu vitamin C")
        if profile.preferred_texture:
            hints.append(f"kết cấu mong muốn: {profile.preferred_texture}")
        if profile.budget_hint:
            hints.append(f"ngân sách khoảng {self._format_vnd(profile.budget_hint)}")

        return ", ".join(hints) if hints else "chưa có sở thích rõ ràng"
