from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agentscore.models import Profile, ScanResult

AGENTSCORE_DIR = Path.home() / ".agentscore"
HISTORY_DIR = AGENTSCORE_DIR / "history"
CONFIG_FILE = AGENTSCORE_DIR / "config.json"
HISTORY_RETENTION_DAYS = 30
TIMESTAMP_FMT = "%Y%m%d_%H%M%S"


def save_result(result: ScanResult) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(tz=timezone.utc)
    filename = ts.strftime(TIMESTAMP_FMT) + ".json"
    path = HISTORY_DIR / filename

    record = {
        "timestamp": result.timestamp,
        "profile": {"role": result.profile.role, "tier": result.profile.tier},
        "total_score": result.total_score,
        "grade": result.grade,
        "scores": result.scores,
        "tool_count": len(result.tool_rois) if result.tool_rois else 0,
        "issues_count": len(result.issues),
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    _prune_old_entries()
    return path


def save_result_with_tools(result: ScanResult, tool_count: int) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(tz=timezone.utc)
    filename = ts.strftime(TIMESTAMP_FMT) + ".json"
    path = HISTORY_DIR / filename

    record = {
        "timestamp": result.timestamp,
        "profile": {"role": result.profile.role, "tier": result.profile.tier},
        "total_score": result.total_score,
        "grade": result.grade,
        "scores": result.scores,
        "tool_count": tool_count,
        "issues_count": len(result.issues),
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    _prune_old_entries()
    return path


def list_history(limit: int = 10) -> list[dict]:
    if not HISTORY_DIR.exists():
        return []

    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    results: list[dict] = []
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            results.append(data)
        except Exception:
            pass
    return results


def load_by_date(date_str: str) -> dict | None:
    if not HISTORY_DIR.exists():
        return None

    for f in sorted(HISTORY_DIR.glob("*.json"), reverse=True):
        if f.name.startswith(date_str.replace("-", "")):
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                pass
    return None


def load_latest() -> dict | None:
    records = list_history(limit=1)
    return records[0] if records else None


def save_config(profile: Profile) -> None:
    AGENTSCORE_DIR.mkdir(parents=True, exist_ok=True)
    config = {
        "profile": {"role": profile.role, "tier": profile.tier},
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config() -> dict | None:
    if not CONFIG_FILE.exists():
        return None
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _prune_old_entries() -> None:
    now = datetime.now(tz=timezone.utc)
    for f in HISTORY_DIR.glob("*.json"):
        try:
            ts = datetime.strptime(f.stem, TIMESTAMP_FMT).replace(tzinfo=timezone.utc)
            if (now - ts).days > HISTORY_RETENTION_DAYS:
                f.unlink()
        except Exception:
            pass
