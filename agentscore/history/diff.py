from __future__ import annotations

from dataclasses import dataclass

DIMENSION_LABELS = {
    "context_efficiency": "Context Efficiency",
    "coverage":           "Coverage",
    "conflict":           "Conflict Detection",
    "config_quality":     "Config Quality",
    "security":           "Security",
    "freshness":          "Freshness",
}


@dataclass
class DiffResult:
    before: dict
    after: dict
    total_delta: float
    dimension_deltas: dict[str, float]
    tool_count_delta: int


def compute_diff(before: dict, after: dict) -> DiffResult:
    before_scores = before.get("scores", {})
    after_scores = after.get("scores", {})

    dimension_deltas = {
        dim: round(after_scores.get(dim, 0.0) - before_scores.get(dim, 0.0), 1)
        for dim in DIMENSION_LABELS
    }

    total_delta = round(
        after.get("total_score", 0.0) - before.get("total_score", 0.0), 1
    )
    tool_count_delta = after.get("tool_count", 0) - before.get("tool_count", 0)

    return DiffResult(
        before=before,
        after=after,
        total_delta=total_delta,
        dimension_deltas=dimension_deltas,
        tool_count_delta=tool_count_delta,
    )
