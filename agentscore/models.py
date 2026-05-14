from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Profile:
    role: str   # 'backend' | 'frontend' | 'fullstack' | 'ml' | 'devops' | 'generic'
    tier: int   # 0=범용, 1=역할선택, 2=상세설정


@dataclass
class Tool:
    id: str                        # "bkit@bkit-marketplace" 또는 "context7"
    display_name: str
    path: Path | None              # 로컬 설치 경로 (MCP는 None일 수 있음)
    context_cost: str              # 'low' | 'medium' | 'high'
    config_priority: str           # 'high' | 'medium' | 'low'
    category: str
    profile_fit: list[str]
    provides: list[str]            # 기능 카테고리 (충돌 감지용)
    in_registry: bool
    last_updated: datetime | None  # installed_plugins.json의 lastUpdated


@dataclass
class Conflict:
    category: str       # 충돌하는 기능 카테고리
    tools: list[Tool]
    message: str


@dataclass
class Issue:
    severity: str       # 'error' | 'warning' | 'info'
    dimension: str      # 평가 차원 이름
    message: str
    recommendation: str


@dataclass
class ToolROI:
    tool_id: str
    config_priority: str
    context_cost: str
    roi_score: float
    verdict: str        # 'keep' | 'review' | 'remove'
    reason: str


@dataclass
class EnvSnapshot:
    claude_version: str
    global_claude_md_content: str      # ~/.claude/CLAUDE.md 단독
    all_claude_md_content: str         # 전역 + 프로젝트 CLAUDE.md 합산
    installed_tools: list[Tool]
    settings: dict                     # ~/.claude/settings.json
    local_settings: dict               # ~/.claude/settings.local.json
    mcp_settings: dict                 # ~/.claude/mcp.json
    installed_plugins: dict            # installed_plugins.json → plugins 키
    scan_timestamp: str


@dataclass
class ScanResult:
    timestamp: str
    profile: Profile
    scores: dict[str, float]           # dimension → score
    total_score: float
    grade: str                         # 'S' | 'A' | 'B' | 'C' | 'D'
    issues: list[Issue]
    recommendations: list[str]
    tool_rois: list[ToolROI]
    conflicts: list[Conflict]
