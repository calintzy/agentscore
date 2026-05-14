from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from agentscore.checker.github_fetcher import RepoInfo
from agentscore.checker.tool_classifier import ClassifiedTool
from agentscore.checker.impact_simulator import SimulationResult

RECOMMENDATION_STYLE = {
    "install":     ("bold green",  "✅ 설치 권장"),
    "skip":        ("bold red",    "❌ 설치 비권장"),
    "conditional": ("bold yellow", "⚠  조건부 권장"),
}

DIMENSION_LABELS = {
    "context_efficiency": "Context Efficiency",
    "coverage":           "Coverage",
    "conflict":           "Conflict Detection",
    "config_quality":     "Config Quality",
    "security":           "Security",
    "freshness":          "Freshness",
}


def print_check_result(
    info: RepoInfo,
    classified: ClassifiedTool,
    result: SimulationResult,
    *,
    no_color: bool = False,
) -> None:
    console = Console(no_color=no_color, highlight=False)

    console.print()
    console.print(f"[bold cyan]agentscore check[/bold cyan] — {info.owner}/{info.repo}", highlight=False)
    console.print(f"[dim]{info.description}[/dim]", highlight=False)
    console.print(f"{result.github_signal}", highlight=False)
    console.print()

    style, label = RECOMMENDATION_STYLE.get(result.recommendation, ("", ""))
    console.print(f"[{style}]{label}[/{style}]  {result.reason}", highlight=False)
    console.print()

    _print_score_delta(console, result)

    _print_tool_info(console, info, classified, result)


def _print_score_delta(console: Console, result: SimulationResult) -> None:
    delta_str = f"{result.score_delta:+.1f}"
    delta_style = "green" if result.score_delta >= 0 else "red"

    console.print(
        f"점수 예측:  {result.before_score:.1f} → [{delta_style}]{result.after_score:.1f} ({delta_str})[/{delta_style}]",
        highlight=False,
    )
    console.print()

    table = Table(box=box.SIMPLE, show_header=True, header_style="dim", pad_edge=False)
    table.add_column("차원", min_width=20)
    table.add_column("현재", justify="right", min_width=6)
    table.add_column("설치 후", justify="right", min_width=8)
    table.add_column("변화", justify="right", min_width=7)

    for dim, label in DIMENSION_LABELS.items():
        before, after = result.score_by_dimension.get(dim, (0.0, 0.0))
        diff = after - before
        if abs(diff) < 0.05:
            diff_str = "  —"
            diff_style = "dim"
        elif diff > 0:
            diff_str = f"+{diff:.1f}"
            diff_style = "green"
        else:
            diff_str = f"{diff:.1f}"
            diff_style = "red"

        table.add_row(
            label,
            f"{before:.1f}",
            f"{after:.1f}",
            f"[{diff_style}]{diff_str}[/{diff_style}]",
        )

    console.print(table)


def _print_tool_info(
    console: Console,
    info: RepoInfo,
    classified: ClassifiedTool,
    result: SimulationResult,
) -> None:
    console.print("[dim]도구 분석:[/dim]", highlight=False)
    console.print(f"  유형: {classified.tool_type}", highlight=False)
    console.print(f"  컨텍스트 비용: {classified.context_cost}", highlight=False)

    if classified.estimated_provides:
        console.print(f"  제공 기능: {', '.join(classified.estimated_provides)}", highlight=False)

    if result.new_provides:
        console.print(f"  새로 추가되는 기능: [green]{', '.join(result.new_provides)}[/green]", highlight=False)

    if result.new_conflicts:
        console.print(f"  충돌 발생: [yellow]{', '.join(result.new_conflicts)}[/yellow]", highlight=False)

    console.print()
