"""6개 평가 차원 단위 테스트."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agentscore.evaluator.config_quality import evaluate_config_quality
from agentscore.evaluator.conflict import detect_conflicts, evaluate_conflict
from agentscore.evaluator.context_efficiency import evaluate_context_efficiency
from agentscore.evaluator.coverage import evaluate_coverage
from agentscore.evaluator.freshness import evaluate_freshness
from agentscore.evaluator.security import (
    CRITICAL_PATTERNS,
    HIGH_PATTERNS,
    MEDIUM_PATTERNS,
    evaluate_security,
)
from agentscore.models import EnvSnapshot, Profile, Tool
from agentscore.profile.profiles import make_profile


# ── 헬퍼 ──────────────────────────────────────────────────────────────────


def _make_env(**kwargs) -> EnvSnapshot:
    defaults = dict(
        claude_version="test",
        global_claude_md_content="",
        all_claude_md_content="",
        installed_tools=[],
        settings={},
        local_settings={},
        mcp_settings={},
        installed_plugins={},
        scan_timestamp="2026-01-01T00:00:00Z",
    )
    return EnvSnapshot(**{**defaults, **kwargs})


def _make_tool(**kwargs) -> Tool:
    defaults = dict(
        path=None,
        last_updated=None,
        in_registry=False,
        provides=[],
        profile_fit=[],
    )
    return Tool(**{**defaults, **kwargs})


def _profile(role: str = "backend") -> Profile:
    return make_profile(role, tier=1)


# ── context_efficiency ────────────────────────────────────────────────────


def test_context_efficiency_baseline():
    env = _make_env()
    score = evaluate_context_efficiency(env, _profile())
    assert score == 25.0


def test_context_efficiency_huge_claude_md():
    huge = "x" * 50000  # ~12,500 토큰, 10,000 초과
    env = _make_env(all_claude_md_content=huge)
    score = evaluate_context_efficiency(env, _profile())
    assert score < 25.0


def test_context_efficiency_dead_weight_tool():
    tool = _make_tool(
        id="heavy",
        display_name="Heavy Unused",
        category="misc",
        context_cost="high",
        config_priority="low",
    )
    env = _make_env(installed_tools=[tool])
    score = evaluate_context_efficiency(env, _profile())
    assert score < 25.0


def test_context_efficiency_ideal_tool_bonus():
    tool = _make_tool(
        id="git-mcp",
        display_name="Git MCP",
        category="git",
        context_cost="low",
        config_priority="high",
        profile_fit=["backend"],
        provides=["git"],
    )
    env = _make_env(installed_tools=[tool])
    score = evaluate_context_efficiency(env, _profile("backend"))
    assert score == 25.0  # 패널티 없음, 보너스로 상한 유지


def test_context_efficiency_duplicate_instructions():
    # _extract_key_clauses는 len >= 30인 줄만 감지
    repeated = "Always respond in Korean and be very helpful.\n" * 5
    env = _make_env(all_claude_md_content=repeated)
    score = evaluate_context_efficiency(env, _profile())
    assert score < 25.0


def test_context_efficiency_never_negative():
    huge = "x" * 200000
    many_heavy = [
        _make_tool(id=f"h{i}", display_name=f"H{i}", category="misc",
                   context_cost="high", config_priority="low")
        for i in range(10)
    ]
    env = _make_env(all_claude_md_content=huge, installed_tools=many_heavy)
    assert evaluate_context_efficiency(env, _profile()) >= 0.0


# ── coverage ─────────────────────────────────────────────────────────────


def test_coverage_generic_profile():
    env = _make_env()
    score = evaluate_coverage(env, make_profile("generic", tier=0))
    assert score == 15.0


def test_coverage_fullstack_all_tools():
    tools = [
        _make_tool(id="db", display_name="DB", category="database",
                   context_cost="low", config_priority="medium", provides=["database"]),
        _make_tool(id="fe", display_name="FE", category="frontend",
                   context_cost="low", config_priority="medium", provides=["frontend"]),
        _make_tool(id="qa", display_name="QA", category="qa",
                   context_cost="low", config_priority="medium", provides=["qa"]),
        _make_tool(id="git", display_name="Git", category="git",
                   context_cost="low", config_priority="medium", provides=["git"]),
    ]
    env = _make_env(installed_tools=tools)
    assert evaluate_coverage(env, _profile("fullstack")) == 20.0


def test_coverage_missing_tools():
    tools = [
        _make_tool(id="qa", display_name="QA", category="qa",
                   context_cost="low", config_priority="medium", provides=["qa"]),
    ]
    env = _make_env(installed_tools=tools)
    score = evaluate_coverage(env, _profile("backend"))  # backend requires db, qa, git
    assert 0.0 < score < 20.0


def test_coverage_no_tools_non_generic():
    env = _make_env()
    score = evaluate_coverage(env, _profile("backend"))
    assert score == 0.0


# ── conflict ─────────────────────────────────────────────────────────────


def test_conflict_no_overlap():
    tools = [
        _make_tool(id="git", display_name="Git", category="git",
                   context_cost="low", config_priority="medium", provides=["git"]),
        _make_tool(id="db", display_name="DB", category="database",
                   context_cost="low", config_priority="medium", provides=["database"]),
    ]
    env = _make_env(installed_tools=tools)
    assert evaluate_conflict(env, _profile()) == 20.0


def test_conflict_two_qa_tools():
    tools = [
        _make_tool(id="qa1", display_name="QA1", category="qa",
                   context_cost="medium", config_priority="medium", provides=["qa"]),
        _make_tool(id="qa2", display_name="QA2", category="qa",
                   context_cost="medium", config_priority="medium", provides=["qa"]),
    ]
    env = _make_env(installed_tools=tools)
    assert evaluate_conflict(env, _profile()) < 20.0


def test_conflict_multitools_exempt():
    tools = [
        _make_tool(id="multi1", display_name="Multi1", category="multi-tool",
                   context_cost="high", config_priority="high",
                   provides=["planning", "git", "qa"]),
        _make_tool(id="multi2", display_name="Multi2", category="multi-tool",
                   context_cost="high", config_priority="medium",
                   provides=["planning", "git", "qa"]),
    ]
    env = _make_env(installed_tools=tools)
    assert evaluate_conflict(env, _profile()) == 20.0


def test_detect_conflicts_returns_category():
    tools = [
        _make_tool(id="qa1", display_name="QA1", category="qa",
                   context_cost="medium", config_priority="medium", provides=["qa"]),
        _make_tool(id="qa2", display_name="QA2", category="qa",
                   context_cost="medium", config_priority="medium", provides=["qa"]),
    ]
    conflicts = detect_conflicts(tools)
    assert len(conflicts) == 1
    assert conflicts[0].category == "qa"
    assert len(conflicts[0].tools) == 2


def test_conflict_never_negative():
    tools = [
        _make_tool(id=f"t{i}", display_name=f"T{i}", category="qa",
                   context_cost="low", config_priority="low", provides=["qa", "git"])
        for i in range(20)
    ]
    env = _make_env(installed_tools=tools)
    assert evaluate_conflict(env, _profile()) >= 0.0


# ── config_quality ────────────────────────────────────────────────────────


def test_config_quality_perfect():
    env = _make_env(
        settings={"model": "claude-opus-4"},
        global_claude_md_content="# Project\n" + "This is a long enough CLAUDE.md file.\n" * 10,
    )
    assert evaluate_config_quality(env, _profile()) == 15.0


def test_config_quality_no_model():
    # 200자 이상 = 50토큰 이상이어야 short 감점(-2) 없음 → 15-3=12
    env = _make_env(
        settings={},
        global_claude_md_content="# Project\n" + "Long content here.\n" * 12,
    )
    score = evaluate_config_quality(env, _profile())
    assert score == 12.0  # 15 - 3


def test_config_quality_no_claude_md():
    env = _make_env(
        settings={"model": "claude-opus-4"},
        global_claude_md_content="",
    )
    score = evaluate_config_quality(env, _profile())
    assert score == 10.0  # 15 - 5


def test_config_quality_short_claude_md():
    env = _make_env(
        settings={"model": "claude-opus-4"},
        global_claude_md_content="Short",  # 토큰 < 50
    )
    score = evaluate_config_quality(env, _profile())
    assert score == 13.0  # 15 - 2


def test_config_quality_disabled_plugins():
    env = _make_env(
        settings={
            "model": "claude-opus-4",
            "enabledPlugins": {"pluginA": False, "pluginB": False},
        },
        global_claude_md_content="# Project\n" + "Long.\n" * 10,
    )
    score = evaluate_config_quality(env, _profile())
    assert score < 15.0


def test_config_quality_never_negative():
    env = _make_env(
        settings={"enabledPlugins": {f"p{i}": False for i in range(20)}},
    )
    assert evaluate_config_quality(env, _profile()) >= 0.0


# ── security ──────────────────────────────────────────────────────────────


def test_security_clean():
    env = _make_env(local_settings={"permissions": {"allow": []}})
    assert evaluate_security(env, _profile()) == 10.0


def test_security_critical_pattern():
    for pattern in CRITICAL_PATTERNS:
        env = _make_env(local_settings={"permissions": {"allow": [pattern]}})
        assert evaluate_security(env, _profile()) == 7.0, f"failed for {pattern}"


def test_security_high_pattern():
    for pattern in HIGH_PATTERNS:
        env = _make_env(local_settings={"permissions": {"allow": [pattern]}})
        score = evaluate_security(env, _profile())
        assert score == 8.0, f"failed for {pattern}"


def test_security_medium_pattern():
    for pattern in MEDIUM_PATTERNS:
        env = _make_env(local_settings={"permissions": {"allow": [pattern]}})
        assert evaluate_security(env, _profile()) == 9.0, f"failed for {pattern}"


def test_security_enable_all_mcp():
    env = _make_env(local_settings={"enableAllProjectMcpServers": True})
    assert evaluate_security(env, _profile()) == 9.0


def test_security_multiple_patterns_accumulate():
    env = _make_env(local_settings={
        "permissions": {"allow": ["Bash(*)", "Bash(rm:*)", "Bash(curl:*)"]},
    })
    # 10 - 3(critical) - 2(high) - 1(medium) = 4
    assert evaluate_security(env, _profile()) == 4.0


def test_security_never_negative():
    patterns = list(CRITICAL_PATTERNS) + list(HIGH_PATTERNS) + list(MEDIUM_PATTERNS)
    env = _make_env(local_settings={
        "permissions": {"allow": patterns},
        "enableAllProjectMcpServers": True,
    })
    assert evaluate_security(env, _profile()) >= 0.0


# ── freshness ─────────────────────────────────────────────────────────────


def _days_ago(n: int) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=n)


def test_freshness_no_tools():
    env = _make_env()
    assert evaluate_freshness(env, _profile()) == 10.0


def test_freshness_no_last_updated():
    tool = _make_tool(id="t", display_name="T", category="qa",
                      context_cost="low", config_priority="medium",
                      last_updated=None)
    env = _make_env(installed_tools=[tool])
    assert evaluate_freshness(env, _profile()) == 10.0


def test_freshness_recent_tool():
    tool = _make_tool(id="t", display_name="T", category="qa",
                      context_cost="low", config_priority="medium",
                      last_updated=_days_ago(30))
    env = _make_env(installed_tools=[tool])
    assert evaluate_freshness(env, _profile()) == 10.0


def test_freshness_moderately_stale():
    tool = _make_tool(id="t", display_name="T", category="qa",
                      context_cost="low", config_priority="medium",
                      last_updated=_days_ago(100))
    env = _make_env(installed_tools=[tool])
    assert evaluate_freshness(env, _profile()) == 9.5  # -0.5


def test_freshness_very_stale():
    tool = _make_tool(id="t", display_name="T", category="qa",
                      context_cost="low", config_priority="medium",
                      last_updated=_days_ago(200))
    env = _make_env(installed_tools=[tool])
    assert evaluate_freshness(env, _profile()) == 8.5  # -1.5


def test_freshness_multiple_stale_tools():
    tools = [
        _make_tool(id=f"t{i}", display_name=f"T{i}", category="qa",
                   context_cost="low", config_priority="medium",
                   last_updated=_days_ago(200))
        for i in range(10)
    ]
    env = _make_env(installed_tools=tools)
    assert evaluate_freshness(env, _profile()) >= 0.0
