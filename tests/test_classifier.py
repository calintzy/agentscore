"""tool_classifier 단위 테스트."""
from __future__ import annotations

from agentscore.checker.github_fetcher import RepoInfo
from agentscore.checker.tool_classifier import (
    ClassifiedTool,
    _detect_tool_type,
    _estimate_context_cost,
    _infer_category,
    _infer_profile_fit,
    _infer_provides,
    classify_tool,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────


def _make_info(**kwargs) -> RepoInfo:
    defaults = dict(
        owner="testuser",
        repo="test-tool",
        stars=0,
        description="",
        license="MIT",
        default_branch="main",
        last_pushed_at="2026-01-01T00:00:00Z",
        open_issues=0,
        topics=[],
        files=[],
        readme="",
        claude_md="",
        raw_files={},
    )
    return RepoInfo(**{**defaults, **kwargs})


# ── _detect_tool_type ─────────────────────────────────────────────────────


def test_detect_plugin_by_skills_dir():
    info = _make_info(files=["skills", "README.md"])
    assert _detect_tool_type(info) == "plugin"


def test_detect_plugin_by_hooks_dir():
    info = _make_info(files=["hooks", "README.md"])
    assert _detect_tool_type(info) == "plugin"


def test_detect_plugin_by_claude_md():
    info = _make_info(claude_md="# My Plugin\nSome instructions.")
    assert _detect_tool_type(info) == "plugin"


def test_detect_plugin_by_topic():
    info = _make_info(topics=["claude-plugin", "ai"])
    assert _detect_tool_type(info) == "plugin"


def test_detect_mcp_server_by_mcp_json():
    info = _make_info(files=["mcp.json", "README.md"])
    assert _detect_tool_type(info) == "mcp_server"


def test_detect_mcp_server_by_dotmcp_json():
    info = _make_info(files=[".mcp.json", "src"])
    assert _detect_tool_type(info) == "mcp_server"


def test_detect_mcp_server_by_topic():
    info = _make_info(topics=["mcp", "server"])
    assert _detect_tool_type(info) == "mcp_server"


def test_detect_mcp_server_by_package_json():
    info = _make_info(raw_files={"package.json": '{"mcpServers": {}}'})
    assert _detect_tool_type(info) == "mcp_server"


def test_detect_library_by_pyproject():
    info = _make_info(files=["pyproject.toml", "src"])
    assert _detect_tool_type(info) == "library"


def test_detect_library_by_setup_py():
    info = _make_info(files=["setup.py", "src"])
    assert _detect_tool_type(info) == "library"


def test_detect_library_by_cargo_toml():
    info = _make_info(files=["Cargo.toml", "src"])
    assert _detect_tool_type(info) == "library"


def test_plugin_beats_library():
    """플러그인 시그널이 있으면 라이브러리가 있어도 plugin으로 분류."""
    info = _make_info(files=["pyproject.toml", "skills"], claude_md="# Plugin")
    assert _detect_tool_type(info) == "plugin"


def test_detect_unknown():
    info = _make_info(files=["README.md", "LICENSE"])
    assert _detect_tool_type(info) == "unknown"


# ── _estimate_context_cost ────────────────────────────────────────────────


def test_mcp_server_always_low_cost():
    info = _make_info(readme="UserPromptSubmit" * 100, claude_md="x" * 10000)
    assert _estimate_context_cost(info, "mcp_server") == "low"


def test_high_cost_when_userpromptsubmit_and_large_claude_md():
    large_claude_md = "x" * 20005  # 20005//4=5001 > 5000 토큰
    info = _make_info(readme="UserPromptSubmit hook enabled", claude_md=large_claude_md)
    assert _estimate_context_cost(info, "plugin") == "high"


def test_high_cost_when_userpromptsubmit_and_many_skills():
    # 11개 이상 헤딩 → skill_count_hint > 10
    many_headings = "\n".join(f"# Skill {i}" for i in range(12))
    info = _make_info(readme=f"UserPromptSubmit\n{many_headings}", claude_md="")
    assert _estimate_context_cost(info, "plugin") == "high"


def test_medium_cost_userpromptsubmit_alone():
    info = _make_info(readme="This hook uses UserPromptSubmit to intercept.", claude_md="short")
    assert _estimate_context_cost(info, "plugin") == "medium"


def test_medium_cost_large_claude_md_no_hook():
    large = "x" * 8005  # 8005//4=2001 > 2000 토큰
    info = _make_info(readme="", claude_md=large)
    assert _estimate_context_cost(info, "plugin") == "medium"


def test_low_cost_small_plugin():
    info = _make_info(readme="A small utility plugin.", claude_md="# Help\nDo X.")
    assert _estimate_context_cost(info, "plugin") == "low"


# ── _infer_provides ───────────────────────────────────────────────────────


def test_provides_requires_two_hits_for_planning():
    # "plan"만 한 번 → 임계값 2 미만, planning 미포함
    info = _make_info(description="A plan tool", topics=[], readme="", claude_md="")
    provides = _infer_provides(info)
    assert "planning" not in provides


def test_provides_planning_two_hits():
    # description 두 번 + topics 두 번 → description에 "plan"이 2회 포함됨
    info = _make_info(description="plan and workflow tool", topics=["plan"])
    provides = _infer_provides(info)
    assert "planning" in provides


def test_provides_git_two_keywords():
    info = _make_info(description="git commit helper", topics=["git"])
    provides = _infer_provides(info)
    assert "git" in provides


def test_provides_single_hit_cap_documentation():
    """documentation은 임계값 1 — 한 번 나와도 포함."""
    info = _make_info(description="docs generator", topics=[], readme="", claude_md="")
    provides = _infer_provides(info)
    assert "documentation" in provides


def test_provides_single_hit_cap_infra():
    info = _make_info(description="infra automation", topics=[], readme="", claude_md="")
    provides = _infer_provides(info)
    assert "infra" in provides


def test_provides_capped_at_six():
    # 6개 초과로 매칭되는 시나리오
    readme = (
        "plan autopilot workflow pdca ralph agent "
        "git commit pr branch "
        "test qa lint review debug "
        "ui ux css react "
        "api server rest backend "
        "database sql postgres "
        "docs document readme wiki "
        "architect microservice "
        "docker k8s infra devops "
        "data ml model jupyter "
        "memory context cache"
    )
    info = _make_info(description=readme, readme=readme)
    provides = _infer_provides(info)
    assert len(provides) <= 6


def test_provides_empty_for_unrelated_readme():
    info = _make_info(description="hello world example", readme="prints greeting", claude_md="")
    provides = _infer_provides(info)
    assert "git" not in provides
    assert "qa" not in provides


# ── _infer_profile_fit ────────────────────────────────────────────────────


def test_profile_fit_excludes_frontend_when_no_frontend_keywords():
    info = _make_info(description="backend api server", readme="rest api", topics=["api"])
    provides = ["backend"]
    fit = _infer_profile_fit(info, provides)
    assert "frontend" not in fit


def test_profile_fit_excludes_ml_when_no_ml_keywords():
    info = _make_info(description="git workflow tool", readme="commit and push", topics=[])
    provides = ["git"]
    fit = _infer_profile_fit(info, provides)
    assert "ml" not in fit


def test_profile_fit_excludes_devops_when_no_devops_keywords():
    info = _make_info(description="code review helper", readme="review pull requests", topics=[])
    provides = ["qa"]
    fit = _infer_profile_fit(info, provides)
    assert "devops" not in fit


def test_profile_fit_includes_all_when_generic():
    """아무 제외 조건도 없으면 모든 프로필 반환."""
    info = _make_info(
        description="react ui css tailwind ml data docker k8s devops",
        readme="frontend ml devops",
        topics=[],
    )
    provides = []
    fit = _infer_profile_fit(info, provides)
    assert set(fit) == {"backend", "frontend", "fullstack", "ml", "devops"}


def test_profile_fit_frontend_included_when_react_in_description():
    info = _make_info(description="react component library", readme="", topics=[])
    provides = ["frontend"]
    fit = _infer_profile_fit(info, provides)
    assert "frontend" in fit


# ── _infer_category ───────────────────────────────────────────────────────


def test_category_planning_priority():
    provides = ["planning", "git", "qa"]
    assert _infer_category(provides, "plugin") == "planning"


def test_category_database_priority_over_qa():
    provides = ["qa", "database"]
    assert _infer_category(provides, "plugin") == "database"


def test_category_unknown_when_no_provides():
    assert _infer_category([], "plugin") == "unknown"


def test_category_fallback_to_first():
    provides = ["debugging"]
    assert _infer_category(provides, "plugin") == "debugging"


# ── classify_tool (통합) ──────────────────────────────────────────────────


def test_classify_mcp_server_integration():
    info = _make_info(
        repo="my-db-server",
        description="PostgreSQL MCP server",
        topics=["mcp", "postgres"],
        files=["mcp.json"],
        readme="A database MCP server for postgres sql queries.",
    )
    result = classify_tool(info)
    assert isinstance(result, ClassifiedTool)
    assert result.tool_type == "mcp_server"
    assert result.context_cost == "low"
    assert "database" in result.estimated_provides
    assert result.install_id == "my-db-server@testuser"


def test_classify_plugin_integration():
    info = _make_info(
        repo="git-plugin",
        description="git commit workflow plugin",
        topics=["claude-plugin", "git"],
        files=["skills", "hooks"],
        claude_md="# Git Plugin\nAutomates git workflows.",
        readme="Handles git commit pr branch workflows.",
    )
    result = classify_tool(info)
    assert result.tool_type == "plugin"
    assert "git" in result.estimated_provides
    assert result.category == "git"


def test_classify_library_integration():
    info = _make_info(
        repo="mylib",
        description="Python utility library",
        files=["pyproject.toml", "src"],
        readme="Install with pip install mylib.",
    )
    result = classify_tool(info)
    assert result.tool_type == "library"
    assert result.display_name == "mylib"
