from __future__ import annotations

from agentscore.evaluator.base import estimate_tokens
from agentscore.models import EnvSnapshot, Profile


def evaluate_config_quality(env: EnvSnapshot, profile: Profile) -> float:
    score = 15.0

    if not env.settings.get("model"):
        score -= 3.0

    disabled = [
        k for k, v in env.settings.get("enabledPlugins", {}).items() if not v
    ]
    score -= min(5.0, len(disabled) * 1.5)

    global_md = env.global_claude_md_content.strip()
    if not global_md:
        score -= 5.0
    elif estimate_tokens(global_md) < 50:
        score -= 2.0

    return max(0.0, score)
