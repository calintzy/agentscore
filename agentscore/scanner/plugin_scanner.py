from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from agentscore.models import EnvSnapshot, Tool

CLAUDE_DIR = Path.home() / ".claude"
_REGISTRY_PATH = Path(__file__).parent.parent / "data" / "tool_registry.json"

_registry_cache: dict | None = None


def _load_registry() -> dict:
    global _registry_cache
    if _registry_cache is None:
        try:
            _registry_cache = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8")).get("tools", {})
        except Exception:
            _registry_cache = {}
    return _registry_cache


def _parse_last_updated(plugin_entries: list) -> datetime | None:
    for entry in plugin_entries:
        raw = entry.get("lastUpdated") or entry.get("installedAt")
        if raw:
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                pass
    return None


def _get_install_path(plugin_entries: list) -> Path | None:
    for entry in plugin_entries:
        p = entry.get("installPath")
        if p:
            return Path(p)
    return None


def _find_plugin_key(tool_id: str, enabled_plugins: dict) -> str | None:
    if tool_id in enabled_plugins:
        return tool_id
    for key in enabled_plugins:
        if key.split("@")[0] == tool_id:
            return key
    return None


def _tool_mentioned_in_claude_md(tool_id: str, content: str) -> bool:
    name = re.escape(tool_id.split("@")[0])
    return bool(re.search(r"\b" + name + r"\b", content, re.IGNORECASE))


def get_config_priority(tool_id: str, env: EnvSnapshot) -> str:
    if _tool_mentioned_in_claude_md(tool_id, env.all_claude_md_content):
        return "high"

    enabled_plugins = env.settings.get("enabledPlugins", {})
    plugin_key = _find_plugin_key(tool_id, enabled_plugins)
    if plugin_key and enabled_plugins[plugin_key] is True:
        return "medium"

    mcp_id = _registry_mcp_id(tool_id)
    check_ids = {tool_id}
    if mcp_id:
        check_ids.add(mcp_id)

    for cid in check_ids:
        if cid in env.local_settings.get("enabledMcpjsonServers", []):
            return "medium"
        if cid in env.mcp_settings.get("mcpServers", {}):
            return "medium"

    return "low"


def _registry_mcp_id(tool_id: str) -> str | None:
    return _load_registry().get(tool_id, {}).get("mcp_id")


def _make_registry_tool(
    tool_id: str,
    rdata: dict,
    env: EnvSnapshot,
    path: Path | None = None,
    last_updated: datetime | None = None,
) -> Tool:
    return Tool(
        id=tool_id,
        display_name=rdata["display_name"],
        path=path,
        context_cost=rdata["context_cost"],
        config_priority=get_config_priority(tool_id, env),
        category=rdata["category"],
        profile_fit=rdata["profile_fit"],
        provides=rdata["provides"],
        in_registry=True,
        last_updated=last_updated,
    )


def _make_unknown_tool(
    tool_id: str,
    display_name: str,
    env: EnvSnapshot,
    path: Path | None = None,
    last_updated: datetime | None = None,
) -> Tool:
    return Tool(
        id=tool_id,
        display_name=display_name,
        path=path,
        context_cost=_estimate_context_cost(path),
        config_priority=get_config_priority(tool_id, env),
        category="unknown",
        profile_fit=[],
        provides=[],
        in_registry=False,
        last_updated=last_updated,
    )


def _estimate_context_cost(tool_path: Path | None) -> str:
    if tool_path is None:
        return "low"
    try:
        has_always_on_hook = (tool_path / "hooks" / "UserPromptSubmit.sh").exists() or \
                             any(tool_path.rglob("UserPromptSubmit*"))
        skill_count = len(list(tool_path.rglob("*.md"))) if tool_path.exists() else 0
        claude_md = (tool_path / "CLAUDE.md")
        tokens = len(claude_md.read_text(encoding="utf-8")) // 4 if claude_md.exists() else 0

        if has_always_on_hook and (skill_count > 10 or tokens > 5000):
            return "high"
        elif has_always_on_hook or skill_count > 5 or tokens > 2000:
            return "medium"
        return "low"
    except Exception:
        return "low"


def scan_tools(env: EnvSnapshot) -> list[Tool]:
    registry = _load_registry()
    tools: dict[str, Tool] = {}

    mcp_id_to_plugin: dict[str, str] = {}
    for rid, rdata in registry.items():
        if "mcp_id" in rdata:
            mcp_id_to_plugin[rdata["mcp_id"]] = rid

    enabled_plugins: dict[str, bool] = env.settings.get("enabledPlugins", {})
    installed_plugins: dict[str, list] = env.installed_plugins

    for plugin_key, active in enabled_plugins.items():
        plugin_name = plugin_key.split("@")[0]
        tool_id = plugin_key if plugin_key in registry else \
                  next((k for k in registry if k.split("@")[0] == plugin_name), None)

        if tool_id is None:
            tool_id = plugin_key

        if tool_id in tools:
            continue

        entries = installed_plugins.get(plugin_key, [])
        install_path = _get_install_path(entries)
        last_updated = _parse_last_updated(entries)

        rdata = registry.get(tool_id)
        if rdata:
            tool = _make_registry_tool(tool_id, rdata, env, install_path, last_updated)
        else:
            tool = _make_unknown_tool(tool_id, plugin_name, env, install_path, last_updated)
        tools[tool_id] = tool

    for mcp_key in env.mcp_settings.get("mcpServers", {}):
        canonical_id = mcp_id_to_plugin.get(mcp_key)
        if canonical_id and canonical_id in tools:
            continue
        tool_id = canonical_id or mcp_key
        if tool_id in tools:
            continue
        rdata = registry.get(tool_id)
        if rdata:
            tools[tool_id] = _make_registry_tool(tool_id, rdata, env)
        else:
            tools[tool_id] = _make_unknown_tool(tool_id, mcp_key, env)

    for mcp_key in env.local_settings.get("enabledMcpjsonServers", []):
        tool_id = mcp_id_to_plugin.get(mcp_key) or mcp_key
        if tool_id in tools:
            continue
        rdata = registry.get(tool_id)
        if rdata:
            tools[tool_id] = _make_registry_tool(tool_id, rdata, env)
        else:
            tools[tool_id] = _make_unknown_tool(tool_id, mcp_key, env)

    return list(tools.values())
