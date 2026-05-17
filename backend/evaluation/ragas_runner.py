from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvaluationResult:
    context_precision: float
    context_recall: float
    faithfulness: float
    notes: str


def run_mock_evaluation() -> EvaluationResult:
    """
    Placeholder hook for integrating RAGAS/TruLens in Phase 3.
    Replace this function with real dataset-based evaluation pipeline.
    """
    return EvaluationResult(
        context_precision=0.0,
        context_recall=0.0,
        faithfulness=0.0,
        notes="Evaluation scaffold ready. Integrate RAGAS/TruLens runners.",
    )
