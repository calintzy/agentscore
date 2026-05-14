from __future__ import annotations

from datetime import datetime, timezone

from agentscore.models import EnvSnapshot, Profile


def evaluate_freshness(env: EnvSnapshot, profile: Profile) -> float:
    score = 10.0
    now = datetime.now(tz=timezone.utc)

    for tool in env.installed_tools:
        if not tool.last_updated:
            continue
        days_old = (now - tool.last_updated).days
        if days_old > 180:
            score -= 1.5
        elif days_old > 90:
            score -= 0.5

    return max(0.0, score)
