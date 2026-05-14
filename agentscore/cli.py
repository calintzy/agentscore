from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import click

from agentscore import __version__
from agentscore.evaluator.config_quality import evaluate_config_quality
from agentscore.evaluator.conflict import detect_conflicts, evaluate_conflict
from agentscore.evaluator.context_efficiency import evaluate_context_efficiency
from agentscore.evaluator.coverage import evaluate_coverage
from agentscore.evaluator.freshness import evaluate_freshness
from agentscore.evaluator.security import evaluate_security
from agentscore.checker.github_fetcher import fetch_repo_info
from agentscore.checker.impact_simulator import simulate_impact
from agentscore.checker.tool_classifier import classify_tool
from agentscore.history.diff import compute_diff
from agentscore.history.store import (
    list_history,
    load_by_date,
    load_config,
    load_latest,
    save_config,
    save_result_with_tools,
)
from agentscore.models import Issue, Profile, ScanResult
from agentscore.profile.detector import detect_profile
from agentscore.profile.profiles import VALID_ROLES, make_profile
from agentscore.reporter.check_reporter import print_check_result
from agentscore.reporter.history_reporter import print_diff, print_history
from agentscore.reporter.terminal import print_scan_result, print_score_result
from agentscore.scanner.config_reader import read_env_snapshot
from agentscore.scanner.plugin_scanner import scan_tools


def _compute_grade(total: float) -> str:
    if total >= 90:
        return "S"
    elif total >= 75:
        return "A"
    elif total >= 55:
        return "B"
    elif total >= 35:
        return "C"
    return "D"


def _run_evaluators(env, profile: Profile) -> ScanResult:
    scores = {
        "context_efficiency": evaluate_context_efficiency(env, profile),
        "coverage":           evaluate_coverage(env, profile),
        "conflict":           evaluate_conflict(env, profile),
        "config_quality":     evaluate_config_quality(env, profile),
        "security":           evaluate_security(env, profile),
        "freshness":          evaluate_freshness(env, profile),
    }
    total = round(sum(scores.values()), 1)
    grade = _compute_grade(total)

    issues: list[Issue] = _generate_issues(env, profile, scores)
    conflicts = detect_conflicts(env.installed_tools)

    return ScanResult(
        timestamp=env.scan_timestamp,
        profile=profile,
        scores=scores,
        total_score=total,
        grade=grade,
        issues=issues,
        recommendations=[],
        tool_rois=[],
        conflicts=conflicts,
    )


def _generate_issues(env, profile: Profile, scores: dict) -> list[Issue]:
    issues: list[Issue] = []

    if scores["security"] < 7.0:
        issues.append(Issue(
            severity="warning",
            dimension="security",
            message="위험한 권한이 허용됨",
            recommendation="settings.local.json의 permissions.allow를 검토하세요",
        ))

    if scores["coverage"] < 10.0 and profile.role != "generic":
        issues.append(Issue(
            severity="warning",
            dimension="coverage",
            message=f"{profile.role} 프로필에 필수 도구가 부족함",
            recommendation="필수 카테고리(git, qa 등) 도구를 추가하세요",
        ))

    if scores["conflict"] < 16.0:
        issues.append(Issue(
            severity="info",
            dimension="conflict",
            message="기능 중복 도구가 감지됨",
            recommendation="동일 기능을 제공하는 도구 중 하나를 제거하세요",
        ))

    if scores["config_quality"] < 10.0:
        issues.append(Issue(
            severity="info",
            dimension="config_quality",
            message="설정 품질 개선 필요",
            recommendation="~/.claude/CLAUDE.md를 작성하고 model을 명시적으로 설정하세요",
        ))

    if scores["freshness"] < 7.0:
        issues.append(Issue(
            severity="info",
            dimension="freshness",
            message="업데이트가 오래된 도구가 있음",
            recommendation="플러그인을 최신 버전으로 업데이트하세요",
        ))

    return issues


@click.group(invoke_without_command=True)
@click.version_option(__version__, "--version", "-V", message="agentscore %(version)s")
@click.option("--profile", "profile_role", default=None, help="역할 지정 (backend/frontend/fullstack/ml/devops)")
@click.option("--json", "output_json", is_flag=True, help="JSON으로 출력")
@click.option("--no-color", is_flag=True, help="색상 없이 출력")
@click.pass_context
def cli(ctx: click.Context, profile_role: str | None, output_json: bool, no_color: bool) -> None:
    """AI 개발 환경 품질 분석 도구."""
    if ctx.invoked_subcommand is not None:
        return

    env = read_env_snapshot()
    tools = scan_tools(env)
    env.installed_tools = tools

    if profile_role:
        profile = make_profile(profile_role, tier=1)
    else:
        saved = load_config()
        if saved:
            profile = make_profile(saved["profile"]["role"], saved["profile"].get("tier", 1))
        else:
            profile = detect_profile()

    result = _run_evaluators(env, profile)

    save_result_with_tools(result, len(tools))

    if output_json:
        output = {
            "timestamp": result.timestamp,
            "profile": {"role": result.profile.role, "tier": result.profile.tier},
            "total_score": result.total_score,
            "grade": result.grade,
            "scores": result.scores,
            "tool_count": len(tools),
            "tools": [
                {
                    "id": t.id,
                    "display_name": t.display_name,
                    "category": t.category,
                    "context_cost": t.context_cost,
                    "config_priority": t.config_priority,
                    "in_registry": t.in_registry,
                    "provides": t.provides,
                }
                for t in tools
            ],
            "issues": [
                {
                    "severity": i.severity,
                    "dimension": i.dimension,
                    "message": i.message,
                    "recommendation": i.recommendation,
                }
                for i in result.issues
            ],
        }
        click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        return

    print_scan_result(env, tools, no_color=no_color)
    print_score_result(result, no_color=no_color)


@cli.command(name="history")
@click.option("--limit", default=10, show_default=True, help="표시할 항목 수")
@click.option("--no-color", is_flag=True)
def history_cmd(limit: int, no_color: bool) -> None:
    """점수 추이를 조회합니다."""
    records = list_history(limit=limit)
    print_history(records, no_color=no_color)


@cli.command()
@click.argument("date", required=False, default=None)
@click.option("--no-color", is_flag=True)
def diff(date: str | None, no_color: bool) -> None:
    """특정 시점 대비 현재 점수를 비교합니다."""
    records = list_history(limit=2)

    if len(records) < 2 and date is None:
        click.echo("비교할 히스토리가 부족합니다. agentscore를 한 번 더 실행한 뒤 시도하세요.")
        return

    if date:
        before = load_by_date(date)
        if not before:
            click.echo(f"날짜 {date}에 해당하는 히스토리를 찾을 수 없습니다.")
            return
        after = records[0]
    else:
        after = records[0]
        before = records[1]

    result = compute_diff(before, after)
    print_diff(result, no_color=no_color)


@cli.command()
@click.option("--profile", "profile_role", default=None,
              help=f"역할 지정 ({'/'.join(sorted(VALID_ROLES - {'generic'}))})")
@click.option("--no-color", is_flag=True)
def setup(profile_role: str | None, no_color: bool) -> None:
    """프로필을 설정하고 저장합니다."""
    console_kwargs = {"no_color": no_color}

    if not profile_role:
        click.echo("역할을 선택하세요:")
        roles = sorted(VALID_ROLES - {"generic"})
        for i, r in enumerate(roles, 1):
            click.echo(f"  {i}. {r}")
        choice = click.prompt("번호 입력", type=click.IntRange(1, len(roles)))
        profile_role = roles[choice - 1]

    profile = make_profile(profile_role, tier=1)
    save_config(profile)
    click.echo(f"프로필 저장 완료: {profile_role} (~/.agentscore/config.json)")


@cli.command()
@click.argument("github_url")
@click.option("--profile", "profile_role", default=None, help="역할 지정")
@click.option("--json", "output_json", is_flag=True, help="JSON으로 출력")
@click.option("--no-color", is_flag=True, help="색상 없이 출력")
def check(github_url: str, profile_role: str | None, output_json: bool, no_color: bool) -> None:
    """새 도구를 설치하기 전 영향을 시뮬레이션합니다."""
    import sys

    env = read_env_snapshot()
    tools = scan_tools(env)
    env.installed_tools = tools

    profile = make_profile(profile_role, tier=1) if profile_role else detect_profile()

    try:
        click.echo(f"  {github_url} 분석 중...", err=True)
        info = fetch_repo_info(github_url)
    except Exception as e:
        click.echo(f"오류: GitHub 데이터를 가져올 수 없습니다 — {e}", err=True)
        sys.exit(1)

    classified = classify_tool(info)
    result = simulate_impact(env, profile, info, classified)

    if output_json:
        output = {
            "repo": f"{info.owner}/{info.repo}",
            "description": info.description,
            "stars": info.stars,
            "license": info.license,
            "tool_type": classified.tool_type,
            "context_cost": classified.context_cost,
            "estimated_provides": classified.estimated_provides,
            "before_score": result.before_score,
            "after_score": result.after_score,
            "score_delta": result.score_delta,
            "recommendation": result.recommendation,
            "reason": result.reason,
            "new_conflicts": result.new_conflicts,
            "new_provides": result.new_provides,
        }
        click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        return

    print_check_result(info, classified, result, no_color=no_color)


if __name__ == "__main__":
    cli()
