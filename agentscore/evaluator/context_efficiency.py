from __future__ import annotations

from agentscore.evaluator.base import (
    DEAD_WEIGHT_THRESHOLD,
    IDEAL_THRESHOLD,
    calculate_roi,
    context_cost_to_penalty,
    estimate_tokens,
)
from agentscore.models import EnvSnapshot, Profile


def evaluate_context_efficiency(env: EnvSnapshot, profile: Profile) -> float:
    score = 25.0

    total_tokens = estimate_tokens(env.all_claude_md_content)
    if total_tokens > 10000:
        score -= min(8.0, (total_tokens - 10000) / 1000)

    for tool in env.installed_tools:
        roi = calculate_roi(tool, profile)
        if roi < DEAD_WEIGHT_THRESHOLD:
            score -= context_cost_to_penalty(tool.context_cost)
        elif roi > IDEAL_THRESHOLD and tool.context_cost == "low":
            score = min(25.0, score + 0.5)

    duplicates = _detect_duplicate_instructions(env)
    score -= min(8.0, len(duplicates) * 2.0)

    return max(0.0, score)


def _detect_duplicate_instructions(env: EnvSnapshot) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for clause in _extract_key_clauses(env.all_claude_md_content):
        normalized = clause.lower().strip()
        if normalized in seen:
            duplicates.append(clause)
        seen.add(normalized)
    return duplicates


def _extract_key_clauses(content: str) -> list[str]:
    in_code_block = False
    clauses: list[str] = []
    for line in content.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if len(stripped) >= 30:
            clauses.append(stripped)
    return clauses
