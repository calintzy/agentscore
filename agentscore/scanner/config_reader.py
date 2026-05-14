from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from agentscore.models import EnvSnapshot

CLAUDE_DIR = Path.home() / ".claude"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def read_settings() -> dict:
    return _read_json(CLAUDE_DIR / "settings.json")


def read_local_settings() -> dict:
    return _read_json(CLAUDE_DIR / "settings.local.json")


def read_mcp_settings() -> dict:
    return _read_json(CLAUDE_DIR / "mcp.json")


def read_global_claude_md() -> str:
    return _read_text(CLAUDE_DIR / "CLAUDE.md")


def read_project_claude_md() -> str:
    parts = [
        _read_text(Path.cwd() / ".claude" / "CLAUDE.md"),
        _read_text(Path.cwd() / "CLAUDE.md"),
    ]
    return "\n".join(p for p in parts if p)


def read_installed_plugins() -> dict:
    data = _read_json(CLAUDE_DIR / "plugins" / "installed_plugins.json")
    return data.get("plugins", {})


def read_claude_version() -> str:
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def read_env_snapshot() -> EnvSnapshot:
    global_md = read_global_claude_md()
    project_md = read_project_claude_md()
    all_md = "\n".join(filter(None, [global_md, project_md]))

    return EnvSnapshot(
        claude_version=read_claude_version(),
        global_claude_md_content=global_md,
        all_claude_md_content=all_md,
        installed_tools=[],
        settings=read_settings(),
        local_settings=read_local_settings(),
        mcp_settings=read_mcp_settings(),
        installed_plugins=read_installed_plugins(),
        scan_timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )
