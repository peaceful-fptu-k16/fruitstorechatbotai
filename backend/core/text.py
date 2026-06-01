from __future__ import annotations

import unicodedata


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    without_marks = (
        without_marks.replace("đ", "d")
        .replace("Đ", "D")
        .replace("Ä‘", "d")
        .replace("Ä", "D")
    )
    return without_marks.lower().strip()
