from __future__ import annotations

import re

from backend.core.text import normalize_text


FRUIT_ALIASES: tuple[str, ...] = (
    "thanh long",
    "viet quat",
    "xoai",
    "cam",
    "nho",
    "buoi",
    "tao",
    "dua",
    "chuoi",
    "oi",
    "kiwi",
    "le",
    "man",
    "dau",
    "cherry",
)

SHORT_CONTEXTUAL_ALIASES: frozenset[str] = frozenset({"oi", "le"})
FRUIT_CONTEXT_PREFIX_PATTERN = r"(?:qua|trai)(?:\s+cay)?"


def fruit_alias_text_pattern(alias: str) -> str:
    normalized_alias = normalize_text(alias)
    escaped_alias = re.escape(normalized_alias)

    if normalized_alias in SHORT_CONTEXTUAL_ALIASES:
        return rf"(?<!\w){FRUIT_CONTEXT_PREFIX_PATTERN}\s+{escaped_alias}(?!\w)"

    return rf"(?<!\w){escaped_alias}(?!\w)"


def fruit_alias_optional_context_pattern(alias: str) -> str:
    normalized_alias = normalize_text(alias)
    escaped_alias = re.escape(normalized_alias)

    if normalized_alias in SHORT_CONTEXTUAL_ALIASES:
        return fruit_alias_text_pattern(normalized_alias)

    return rf"(?<!\w)(?:{FRUIT_CONTEXT_PREFIX_PATTERN}\s+|san\s+pham\s+)?{escaped_alias}(?!\w)"


def fruit_alias_quantity_pattern(alias: str) -> str:
    normalized_alias = normalize_text(alias)
    escaped_alias = re.escape(normalized_alias)

    if normalized_alias in SHORT_CONTEXTUAL_ALIASES:
        return rf"(?:\b(\d+)\s*)?{FRUIT_CONTEXT_PREFIX_PATTERN}\s+{escaped_alias}(?!\w)"

    return rf"(?:\b(\d+)\s*(?:qua|trai|kg|can)?\s+)?(?<!\w){escaped_alias}(?!\w)"


def fruit_alias_matches_text(alias: str, text: str) -> bool:
    return re.search(fruit_alias_text_pattern(alias), normalize_text(text)) is not None


def extract_fruit_aliases(text: str, aliases: tuple[str, ...] = FRUIT_ALIASES) -> list[str]:
    normalized_text = normalize_text(text)
    matched: list[str] = []
    seen: set[str] = set()

    for alias in sorted(aliases, key=len, reverse=True):
        normalized_alias = normalize_text(alias)
        if normalized_alias in seen:
            continue
        if re.search(fruit_alias_text_pattern(normalized_alias), normalized_text) is None:
            continue
        seen.add(normalized_alias)
        matched.append(normalized_alias)

    return matched


def has_fruit_alias(text: str, aliases: tuple[str, ...] = FRUIT_ALIASES) -> bool:
    return bool(extract_fruit_aliases(text, aliases=aliases))


def has_unqualified_short_alias(text: str) -> bool:
    normalized_text = normalize_text(text)
    for alias in SHORT_CONTEXTUAL_ALIASES:
        has_bare_alias = re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized_text) is not None
        if has_bare_alias and not fruit_alias_matches_text(alias, normalized_text):
            return True
    return False
