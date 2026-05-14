from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from agentscore.checker.github_fetcher import RepoInfo
from agentscore.checker.tool_classifier import ClassifiedTool
from agentscore.evaluator.config_quality import evaluate_config_quality
from agentscore.evaluator.conflict import detect_conflicts, evaluate_conflict
from agentscore.evaluator.context_efficiency import evaluate_context_efficiency
from agentscore.evaluator.coverage import evaluate_coverage
from agentscore.evaluator.freshness import evaluate_freshness
from agentscore.evaluator.security import evaluate_security
from agentscore.models import EnvSnapshot, Profile, Tool


@dataclass
class SimulationResult:
    before_score: float
    after_score: float
    score_delta: float
    score_by_dimension: dict[str, tuple[float, float]]
    recommendation: str       # 'install' | 'skip' | 'conditional'
    reason: str
    new_conflicts: list[str]
    new_provides: list[str]
    github_signal: str        # 신뢰도 요약


def simulate_impact(
    env: EnvSnapshot,
    profile: Profile,
    info: RepoInfo,
    classified: ClassifiedTool,
) -> SimulationResult:
    before_scores = _evaluate_all(env, profile)
    before_total = sum(before_scores.values())

    simulated_tool = _make_simulated_tool(classified, info)
    simulated_env = _clone_env_with_tool(env, simulated_tool)

    after_scores = _evaluate_all(simulated_env, profile)
    after_total = sum(after_scores.values())

    delta = round(after_total - before_total, 1)

    new_conflicts: list[str] = []
    before_conflicts = {c.category for c in detect_conflicts(env.installed_tools)}
    after_conflicts = {c.category for c in detect_conflicts(simulated_env.installed_tools)}
    new_conflicts = list(after_conflicts - before_conflicts)

    existing_provides: set[str] = set()
    for t in env.installed_tools:
        existing_provides.update(t.provides)
    new_provides = [p for p in classified.estimated_provides if p not in existing_provides]

    recommendation, reason = _make_recommendation(
        delta, new_conflicts, classified, profile, info
    )

    github_signal = _summarize_github_signal(info)

    return SimulationResult(
        before_score=round(before_total, 1),
        after_score=round(after_total, 1),
        score_delta=delta,
        score_by_dimension={
            dim: (round(before_scores[dim], 1), round(after_scores[dim], 1))
            for dim in before_scores
        },
        recommendation=recommendation,
        reason=reason,
        new_conflicts=new_conflicts,
        new_provides=new_provides,
        github_signal=github_signal,
    )


def _evaluate_all(env: EnvSnapshot, profile: Profile) -> dict[str, float]:
    return {
        "context_efficiency": evaluate_context_efficiency(env, profile),
        "coverage":           evaluate_coverage(env, profile),
        "conflict":           evaluate_conflict(env, profile),
        "config_quality":     evaluate_config_quality(env, profile),
        "security":           evaluate_security(env, profile),
        "freshness":          evaluate_freshness(env, profile),
    }


def _make_simulated_tool(classified: ClassifiedTool, info: RepoInfo) -> Tool:
    return Tool(
        id=classified.install_id,
        display_name=info.repo,
        path=None,
        context_cost=classified.context_cost,
        config_priority="medium",
        category=classified.category,
        profile_fit=classified.profile_fit,
        provides=classified.estimated_provides,
        in_registry=False,
        last_updated=datetime.now(tz=timezone.utc),
    )


def _clone_env_with_tool(env: EnvSnapshot, new_tool: Tool) -> EnvSnapshot:
    return EnvSnapshot(
        claude_version=env.claude_version,
        global_claude_md_content=env.global_claude_md_content,
        all_claude_md_content=env.all_claude_md_content,
        installed_tools=env.installed_tools + [new_tool],
        settings=env.settings,
        local_settings=env.local_settings,
        mcp_settings=env.mcp_settings,
        installed_plugins=env.installed_plugins,
        scan_timestamp=env.scan_timestamp,
    )


def _make_recommendation(
    delta: float,
    new_conflicts: list[str],
    classified: ClassifiedTool,
    profile: Profile,
    info: RepoInfo,
) -> tuple[str, str]:
    if classified.context_cost == "high" and not classified.estimated_provides:
        return "skip", "컨텍스트 비용이 높고 제공 기능을 파악하기 어렵습니다"

    if new_conflicts and classified.context_cost == "high":
        return "skip", f"기존 도구와 기능 충돌 발생 ({', '.join(new_conflicts)}) + 높은 컨텍스트 비용"

    if delta >= 2.0:
        return "install", f"점수 +{delta:.1f}점 향상 예상"

    if delta >= 0 and not new_conflicts:
        return "conditional", f"소폭 개선 또는 중립 (Δ{delta:+.1f}). 필요에 따라 설치"

    if new_conflicts:
        return "conditional", f"기능 충돌 감지 ({', '.join(new_conflicts)}). 기존 도구 제거 후 설치 권장"

    return "skip", f"설치 시 점수 감소 예상 (Δ{delta:+.1f})"


def _summarize_github_signal(info: RepoInfo) -> str:
    parts = []
    if info.stars >= 1000:
        parts.append(f"⭐ {info.stars:,}stars")
    elif info.stars >= 100:
        parts.append(f"⭐ {info.stars}stars")
    else:
        parts.append(f"⭐ {info.stars}stars (신규/소규모)")

    if info.license:
        parts.append(f"📄 {info.license}")
    else:
        parts.append("📄 라이선스 없음")

    if info.last_pushed_at:
        try:
            pushed = datetime.fromisoformat(info.last_pushed_at.replace("Z", "+00:00"))
            days = (datetime.now(tz=timezone.utc) - pushed).days
            if days < 30:
                parts.append("🟢 최근 업데이트")
            elif days < 180:
                parts.append("🟡 6개월 이내")
            else:
                parts.append(f"🔴 {days}일 전 업데이트")
        except Exception:
            pass

    return "  ".join(parts)
