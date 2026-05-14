from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import click

_INTERACTIVE = "__interactive__"

def _patch_argv_profile() -> None:
    """--profile 뒤에 값이 없으면 인터랙티브 sentinel 삽입."""
    for i, arg in enumerate(sys.argv):
        if arg == "--profile":
            is_last = i == len(sys.argv) - 1
            next_is_flag = (not is_last) and sys.argv[i + 1].startswith("-")
            if is_last or next_is_flag:
                sys.argv.insert(i + 1, _INTERACTIVE)
            break

_patch_argv_profile()

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
from agentscore.i18n import t
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
            message=t("issue_security"),
            recommendation=t("issue_security_rec"),
        ))

    if scores["coverage"] < 10.0 and profile.role != "generic":
        issues.append(Issue(
            severity="warning",
            dimension="coverage",
            message=t("issue_coverage", role=profile.role),
            recommendation=t("issue_coverage_rec"),
        ))

    if scores["conflict"] < 16.0:
        issues.append(Issue(
            severity="info",
            dimension="conflict",
            message=t("issue_conflict"),
            recommendation=t("issue_conflict_rec"),
        ))

    if scores["config_quality"] < 10.0:
        issues.append(Issue(
            severity="info",
            dimension="config_quality",
            message=t("issue_config"),
            recommendation=t("issue_config_rec"),
        ))

    if scores["freshness"] < 7.0:
        issues.append(Issue(
            severity="info",
            dimension="freshness",
            message=t("issue_freshness"),
            recommendation=t("issue_freshness_rec"),
        ))

    return issues


@click.group(invoke_without_command=True)
@click.version_option(__version__, "--version", "-V", message="agentscore %(version)s")
@click.option("--profile", "profile_role", default=None, help=t("opt_profile"))
@click.option("--json", "output_json", is_flag=True, help=t("opt_json"))
@click.option("--no-color", is_flag=True, help=t("opt_no_color"))
@click.pass_context
def cli(ctx: click.Context, profile_role: str | None, output_json: bool, no_color: bool) -> None:
    """AI development environment quality analyzer."""
    if ctx.invoked_subcommand is not None:
        return

    env = read_env_snapshot()
    tools = scan_tools(env)
    env.installed_tools = tools

    if profile_role == _INTERACTIVE:
        click.echo(t("setup_select_role"))
        roles = sorted(VALID_ROLES - {"generic"})
        for i, r in enumerate(roles, 1):
            click.echo(f"  {i}. {r}")
        choice = click.prompt(t("setup_prompt"), type=click.IntRange(1, len(roles)))
        profile_role = roles[choice - 1]
        profile = make_profile(profile_role, tier=1)
        save_config(profile)
        click.echo(t("setup_saved", role=profile_role))
        click.echo()
    elif profile_role:
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
@click.option("--limit", default=10, show_default=True, help=t("opt_limit"))
@click.option("--no-color", is_flag=True)
def history_cmd(limit: int, no_color: bool) -> None:
    """Show score history."""
    records = list_history(limit=limit)
    print_history(records, no_color=no_color)


@cli.command()
@click.argument("date", required=False, default=None)
@click.option("--no-color", is_flag=True)
def diff(date: str | None, no_color: bool) -> None:
    """Compare current score against a previous snapshot."""
    records = list_history(limit=2)

    if len(records) < 2 and date is None:
        click.echo(t("diff_not_enough"))
        return

    if date:
        before = load_by_date(date)
        if not before:
            click.echo(t("diff_not_found", date=date))
            return
        after = records[0]
    else:
        after = records[0]
        before = records[1]

    result = compute_diff(before, after)
    print_diff(result, no_color=no_color)


@cli.command()
@click.option("--profile", "profile_role", default=None, help=t("opt_profile"))
@click.option("--no-color", is_flag=True)
def setup(profile_role: str | None, no_color: bool) -> None:
    """Configure and save your profile."""
    if not profile_role:
        click.echo(t("setup_select_role"))
        roles = sorted(VALID_ROLES - {"generic"})
        for i, r in enumerate(roles, 1):
            click.echo(f"  {i}. {r}")
        choice = click.prompt(t("setup_prompt"), type=click.IntRange(1, len(roles)))
        profile_role = roles[choice - 1]

    profile = make_profile(profile_role, tier=1)
    save_config(profile)
    click.echo(t("setup_saved", role=profile_role))


@cli.command()
@click.argument("github_url")
@click.option("--profile", "profile_role", default=None, help=t("opt_profile"))
@click.option("--json", "output_json", is_flag=True, help=t("opt_json"))
@click.option("--no-color", is_flag=True, help=t("opt_no_color"))
def check(github_url: str, profile_role: str | None, output_json: bool, no_color: bool) -> None:
    """Simulate the impact of installing a new tool."""
    import sys

    env = read_env_snapshot()
    tools = scan_tools(env)
    env.installed_tools = tools

    profile = make_profile(profile_role, tier=1) if profile_role else detect_profile()

    try:
        click.echo(t("check_analyzing", url=github_url), err=True)
        info = fetch_repo_info(github_url)
    except Exception as e:
        click.echo(t("check_error", err=e), err=True)
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
