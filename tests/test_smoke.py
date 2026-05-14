"""기본 임포트 및 동작 검증."""
from __future__ import annotations

from agentscore.checker.github_fetcher import parse_github_url
from agentscore.evaluator.base import calculate_roi, DEAD_WEIGHT_THRESHOLD
from agentscore.models import Tool, Profile
from agentscore.profile.profiles import make_profile, VALID_ROLES


def test_parse_github_url_https():
    owner, repo = parse_github_url("https://github.com/upstash/context7")
    assert owner == "upstash"
    assert repo == "context7"


def test_parse_github_url_short():
    owner, repo = parse_github_url("upstash/context7")
    assert owner == "upstash"
    assert repo == "context7"


def test_valid_roles():
    assert "backend" in VALID_ROLES
    assert "frontend" in VALID_ROLES
    assert "generic" in VALID_ROLES


def test_make_profile():
    p = make_profile("backend", tier=1)
    assert p.role == "backend"
    assert p.tier == 1


def _make_tool(**kwargs) -> Tool:
    defaults = dict(path="", last_updated=None, in_registry=False, provides=[], profile_fit=[])
    return Tool(**{**defaults, **kwargs})


def test_roi_dead_weight():
    tool = _make_tool(
        id="heavy-unused",
        display_name="Heavy Unused",
        category="misc",
        context_cost="high",
        config_priority="low",
    )
    profile = make_profile("backend", tier=1)
    roi = calculate_roi(tool, profile)
    assert roi < DEAD_WEIGHT_THRESHOLD


def test_roi_ideal():
    tool = _make_tool(
        id="git",
        display_name="Git MCP",
        category="git",
        context_cost="low",
        config_priority="high",
        profile_fit=["backend", "frontend", "fullstack", "ml", "devops"],
        provides=["git"],
        in_registry=True,
    )
    profile = make_profile("backend", tier=1)
    roi = calculate_roi(tool, profile)
    assert roi > 1.0
