from __future__ import annotations

from agentscore.models import EnvSnapshot, Profile

PROFILE_REQUIRED: dict[str, set[str]] = {
    "backend":   {"database", "qa", "git"},
    "frontend":  {"frontend", "qa", "git"},
    "fullstack": {"database", "frontend", "qa", "git"},
    "ml":        {"data", "qa", "git"},
    "devops":    {"infra", "qa", "git"},
    "generic":   set(),
}


def evaluate_coverage(env: EnvSnapshot, profile: Profile) -> float:
    required = PROFILE_REQUIRED.get(profile.role, set())
    if not required:
        return 15.0

    installed_provides: set[str] = set()
    for tool in env.installed_tools:
        installed_provides.update(tool.provides)

    covered = installed_provides & required
    return round((len(covered) / len(required)) * 20.0, 1)
