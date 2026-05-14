from __future__ import annotations

from agentscore.models import Profile, Tool

COST_MAP = {"low": 0.2, "medium": 0.5, "high": 1.0}
CONFIG_PRIORITY_TO_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.2}
DEAD_WEIGHT_THRESHOLD = 0.3
IDEAL_THRESHOLD = 2.0


def calculate_roi(tool: Tool, profile: Profile) -> float:
    fit_score = 0.7 if profile.role == "generic" else (
        1.0 if profile.role in tool.profile_fit else 0.3
    )
    freq_score = CONFIG_PRIORITY_TO_SCORE.get(tool.config_priority, 0.2)
    cost = COST_MAP.get(tool.context_cost, 0.5)
    return (fit_score * 0.6 + freq_score * 0.4) / cost


def context_cost_to_penalty(cost: str) -> float:
    return {"low": 0.5, "medium": 2.0, "high": 4.0}.get(cost, 1.0)


def estimate_tokens(text: str) -> int:
    return len(text) // 4
