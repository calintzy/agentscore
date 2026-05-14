from __future__ import annotations

from agentscore.models import Profile

VALID_ROLES = {"backend", "frontend", "fullstack", "ml", "devops", "generic"}


def make_profile(role: str = "generic", tier: int = 0) -> Profile:
    role = role if role in VALID_ROLES else "generic"
    return Profile(role=role, tier=tier)


def generic_profile() -> Profile:
    return Profile(role="generic", tier=0)
