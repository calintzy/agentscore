from __future__ import annotations

from agentscore.models import EnvSnapshot, Profile

HIGH_RISK_PATTERNS = {"Bash(*)", "Bash(rm:*)", "Bash(sudo:*)"}
WARN_RISK_PATTERNS = {"Bash(curl:*)"}


def evaluate_security(env: EnvSnapshot, profile: Profile) -> float:
    score = 10.0
    allow_list = env.local_settings.get("permissions", {}).get("allow", [])

    for pattern in allow_list:
        if pattern in HIGH_RISK_PATTERNS:
            score -= 3.0
        elif pattern in WARN_RISK_PATTERNS:
            score -= 1.0

    if env.local_settings.get("enableAllProjectMcpServers", False):
        score -= 1.0

    return max(0.0, score)
