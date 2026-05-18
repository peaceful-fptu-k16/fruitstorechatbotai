from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from backend.agents.memory_agent import PreferenceProfile
from backend.agents.recommendation_agent import RecommendationAgent
from backend.core.text import normalize_text

FRUIT_ENTITY_ALIASES: tuple[str, ...] = (
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
)

IN_DOMAIN_SIGNALS: tuple[str, ...] = (
    "trai",
    "trai cay",
    "qua",
    "shop",
    "san pham",
    "mat hang",
    "goi y",
    "tu van",
    "ngot",
    "chua",
    "ton kho",
    "con hang",
    "ship",
    "giao",
)


def _extract_entities(text: str) -> list[str]:
    normalized = normalize_text(text)
    entities: list[str] = []
    seen: set[str] = set()
    for alias in sorted(FRUIT_ENTITY_ALIASES, key=len, reverse=True):
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        if re.search(pattern, normalized) is None:
            continue
        if alias in seen:
            continue
        seen.add(alias)
        entities.append(alias)
    return entities


def _extract_answer_prices(answer: str) -> list[int]:
    prices: list[int] = []
    for match in re.finditer(r"(\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(đ|d|vnd|k)", answer.lower()):
        numeric = re.sub(r"[^\d]", "", match.group(1))
        if not numeric:
            continue
        value = int(numeric)
        if match.group(2) == "k" and value < 1000:
            value *= 1000
        prices.append(value)
    return prices


def _price_within_bounds(price: int, min_price: int | None, max_price: int | None) -> bool:
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    return True


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def build_report(log_path: Path) -> dict[str, Any]:
    if not log_path.exists():
        return {
            "path": str(log_path),
            "total": 0,
            "error": "log file not found",
        }

    recommender = RecommendationAgent()

    total = 0
    entity_query_count = 0
    entity_hit_count = 0
    budget_query_count = 0
    budget_constraint_pass_count = 0
    in_domain_query_count = 0
    route_accuracy_count = 0
    entity_specific_query_count = 0
    extraneous_suggestion_count = 0

    review_mode_counts: dict[str, int] = {}
    intent_counts: dict[str, int] = {}

    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = line.strip()
            if not payload:
                continue

            try:
                record = json.loads(payload)
            except Exception:
                continue

            total += 1
            question = str(record.get("question", ""))
            answer = str(record.get("answer", ""))
            intent = str(record.get("intent", ""))

            intent_counts[intent] = intent_counts.get(intent, 0) + 1

            review = record.get("review")
            review_mode = "none"
            if isinstance(review, dict):
                review_mode = str(review.get("review_mode", "none"))
            review_mode_counts[review_mode] = review_mode_counts.get(review_mode, 0) + 1

            question_entities = _extract_entities(question)
            answer_entities = _extract_entities(answer)

            if question_entities:
                entity_query_count += 1
                if any(entity in answer_entities for entity in question_entities):
                    entity_hit_count += 1

                entity_specific_query_count += 1
                extra_entities = [entity for entity in answer_entities if entity not in question_entities]
                if extra_entities:
                    extraneous_suggestion_count += 1

            normalized_question = normalize_text(question)
            in_domain = bool(question_entities) or any(signal in normalized_question for signal in IN_DOMAIN_SIGNALS)
            if in_domain:
                in_domain_query_count += 1
                if intent != "out_of_domain":
                    route_accuracy_count += 1

            constraints = recommender.parse_preferences(question, PreferenceProfile())
            min_price = constraints.get("min_price")
            max_price = constraints.get("max_price") or constraints.get("budget")

            if min_price is not None or max_price is not None:
                budget_query_count += 1
                prices = _extract_answer_prices(answer)
                if prices and all(_price_within_bounds(price, min_price=min_price, max_price=max_price) for price in prices):
                    budget_constraint_pass_count += 1

    return {
        "path": str(log_path),
        "total": total,
        "entity_hit_rate": {
            "pass": entity_hit_count,
            "total": entity_query_count,
            "rate_percent": _safe_ratio(entity_hit_count, entity_query_count),
        },
        "budget_constraint_pass_rate": {
            "pass": budget_constraint_pass_count,
            "total": budget_query_count,
            "rate_percent": _safe_ratio(budget_constraint_pass_count, budget_query_count),
        },
        "route_accuracy_in_domain": {
            "pass": route_accuracy_count,
            "total": in_domain_query_count,
            "rate_percent": _safe_ratio(route_accuracy_count, in_domain_query_count),
        },
        "extraneous_suggestion_rate": {
            "fail": extraneous_suggestion_count,
            "total": entity_specific_query_count,
            "rate_percent": _safe_ratio(extraneous_suggestion_count, entity_specific_query_count),
        },
        "intent_counts": intent_counts,
        "review_mode_counts": review_mode_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build KPI report from qa_pairs.jsonl")
    parser.add_argument(
        "--path",
        default="ai_log/qa_pairs.jsonl",
        help="Path to JSONL log file",
    )
    args = parser.parse_args()

    report = build_report(Path(args.path))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
