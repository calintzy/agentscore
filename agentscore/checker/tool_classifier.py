from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from agentscore.checker.github_fetcher import RepoInfo
from agentscore.evaluator.base import estimate_tokens


@dataclass
class ClassifiedTool:
    tool_type: str           # 'plugin' | 'mcp_server' | 'skill_pack' | 'library' | 'unknown'
    context_cost: str        # 'low' | 'medium' | 'high'
    estimated_provides: list[str]
    profile_fit: list[str]
    install_id: str          # 예상 tool_id (registry 등록용)
    display_name: str
    category: str


_PROVIDES_KEYWORDS: dict[str, list[str]] = {
    "planning":      ["plan", "pdca", "autopilot", "ralph", "workflow", "agent"],
    "git":           ["git", "commit", "pr", "pull request", "branch"],
    "qa":            ["test", "qa", "quality", "lint", "review", "debug"],
    "frontend":      ["ui", "ux", "design", "css", "tailwind", "react", "next"],
    "backend":       ["api", "server", "rest", "backend", "express", "fastapi"],
    "database":      ["db", "database", "sql", "postgres", "mongo", "redis", "supabase"],
    "documentation": ["docs", "document", "readme", "wiki", "notion", "search"],
    "architecture":  ["architect", "design pattern", "ddd", "microservice"],
    "debugging":     ["debug", "trace", "monitor", "log", "sentry", "error"],
    "infra":         ["infra", "devops", "k8s", "kubernetes", "docker", "terraform", "aws"],
    "data":          ["data", "ml", "model", "jupyter", "pandas", "numpy", "dataset"],
    "memory":        ["memory", "context", "persist", "store", "cache"],
}

_ALL_PROFILES = ["backend", "frontend", "fullstack", "ml", "devops"]


def classify_tool(info: RepoInfo) -> ClassifiedTool:
    tool_type = _detect_tool_type(info)
    context_cost = _estimate_context_cost(info, tool_type)
    provides = _infer_provides(info)
    profile_fit = _infer_profile_fit(info, provides)
    install_id = _guess_install_id(info)
    category = _infer_category(provides, tool_type)

    return ClassifiedTool(
        tool_type=tool_type,
        context_cost=context_cost,
        estimated_provides=provides,
        profile_fit=profile_fit,
        install_id=install_id,
        display_name=info.repo,
        category=category,
    )


def _detect_tool_type(info: RepoInfo) -> str:
    files_lower = {f.lower() for f in info.files}

    is_plugin = (
        "skills" in files_lower or
        "hooks" in files_lower or
        bool(info.claude_md) or
        "installed_plugins.json" in files_lower or
        any("plugin" in t for t in info.topics)
    )
    has_mcp = (
        "mcp.json" in files_lower or
        ".mcp.json" in files_lower or
        "mcpServers" in (info.raw_files.get("package.json") or "") or
        any("mcp" in t for t in info.topics)
    )
    is_library = (
        "pyproject.toml" in files_lower or
        "setup.py" in files_lower or
        "cargo.toml" in files_lower
    ) and not is_plugin

    if is_plugin and has_mcp:
        return "plugin"
    if is_plugin:
        return "plugin"
    if has_mcp:
        return "mcp_server"
    if is_library:
        return "library"
    return "unknown"


def _estimate_context_cost(info: RepoInfo, tool_type: str) -> str:
    if tool_type == "mcp_server":
        return "low"

    has_always_on = bool(re.search(r"UserPromptSubmit", info.readme or "", re.IGNORECASE)) or \
                    bool(re.search(r"UserPromptSubmit", info.claude_md or "", re.IGNORECASE))

    readme_tokens = estimate_tokens(info.readme)
    claude_tokens = estimate_tokens(info.claude_md)

    skills_mentioned = bool(re.search(r"\bskills?\b", info.readme, re.IGNORECASE))
    skill_count_hint = len(re.findall(r"^#+\s", info.readme, re.MULTILINE))

    if has_always_on and (claude_tokens > 5000 or skill_count_hint > 10):
        return "high"
    if has_always_on or claude_tokens > 2000 or (skills_mentioned and skill_count_hint > 5):
        return "medium"
    return "low"


_SINGLE_HIT_CAPS = {"documentation", "infra", "data", "memory"}

def _infer_provides(info: RepoInfo) -> list[str]:
    # description+topics은 신뢰도 높으므로 가중치 부여 (두 번 포함)
    text = " ".join([
        info.repo,
        info.description,
        info.description,
        " ".join(info.topics),
        " ".join(info.topics),
        info.readme[:2000],
        info.claude_md[:500],
    ]).lower()

    found: list[str] = []
    for cap, keywords in _PROVIDES_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        threshold = 1 if cap in _SINGLE_HIT_CAPS else 2
        if hits >= threshold:
            found.append(cap)

    return found[:6]


def _infer_profile_fit(info: RepoInfo, provides: list[str]) -> list[str]:
    text = " ".join([info.description, info.readme[:2000], " ".join(info.topics)]).lower()

    exclude: set[str] = set()
    if not any(kw in text for kw in ["frontend", "ui", "react", "css"]):
        exclude.add("frontend")
    if not any(kw in text for kw in ["ml", "data", "jupyter", "model"]):
        exclude.add("ml")
    if not any(kw in text for kw in ["devops", "infra", "k8s", "docker"]):
        exclude.add("devops")

    if not exclude:
        return _ALL_PROFILES

    return [p for p in _ALL_PROFILES if p not in exclude]


def _guess_install_id(info: RepoInfo) -> str:
    return f"{info.repo}@{info.owner}"


def _infer_category(provides: list[str], tool_type: str) -> str:
    if not provides:
        return "unknown"
    priority = ["planning", "database", "frontend", "infra", "data", "qa", "git", "debugging"]
    for p in priority:
        if p in provides:
            return p
    return provides[0]
