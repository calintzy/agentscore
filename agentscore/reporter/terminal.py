from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.columns import Columns
from rich.text import Text
from rich import box

from agentscore.i18n import t
from agentscore.models import EnvSnapshot, ScanResult, Tool

COST_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴"}
PRIORITY_EMOJI = {"high": "⬆", "medium": "➡", "low": "⬇"}
COST_LABEL = {"low": "low", "medium": "med", "high": "high"}

GRADE_COLOR = {
    "S": "bright_cyan",
    "A": "green",
    "B": "yellow",
    "C": "dark_orange",
    "D": "red",
}
GRADE_BADGE = {
    "S": "╔══╗\n║ S║\n╚══╝",
    "A": "╔══╗\n║ A║\n╚══╝",
    "B": "╔══╗\n║ B║\n╚══╝",
    "C": "╔══╗\n║ C║\n╚══╝",
    "D": "╔══╗\n║ D║\n╚══╝",
}

DIMENSION_LABELS = {
    "context_efficiency": "Context Efficiency",
    "coverage":           "Coverage          ",
    "conflict":           "Conflict Detection",
    "config_quality":     "Config Quality    ",
    "security":           "Security          ",
    "freshness":          "Freshness         ",
}

DIMENSION_MAX = {
    "context_efficiency": 25,
    "coverage":           20,
    "conflict":           20,
    "config_quality":     15,
    "security":           10,
    "freshness":          10,
}

BAR_WIDTH = 16


def _generate_tips(result: ScanResult, tools: list[Tool] | None = None) -> list[str]:
    ranked = sorted(
        DIMENSION_MAX.keys(),
        key=lambda d: result.scores.get(d, 0.0) / DIMENSION_MAX[d],
    )
    tips = []
    for dim in ranked:
        ratio = result.scores.get(dim, 0.0) / DIMENSION_MAX[dim]
        if ratio >= 0.85:
            continue
        tip = _specific_tip(dim, result, tools)
        if tip:
            tips.append(tip)
        if len(tips) == 3:
            break
    return tips


def _specific_tip(dim: str, result: ScanResult, tools: list[Tool] | None) -> str:
    if dim == "context_efficiency" and tools:
        heavy = [t.display_name for t in tools if t.context_cost == "high"]
        if heavy:
            names = " · ".join(heavy)
            return t("tip_context_efficiency_specific", names=names)
        return t("tip_context_efficiency")

    if dim == "conflict" and result.conflicts:
        worst = max(result.conflicts, key=lambda c: len(c.tools))
        names = " · ".join(tool.display_name for tool in worst.tools)
        return t("tip_conflict_specific", category=worst.category, names=names)
    if dim == "conflict":
        return t("tip_conflict")

    return t(f"tip_{dim}")


def _bar(score: float, max_score: float) -> str:
    filled = int((score / max_score) * BAR_WIDTH) if max_score else 0
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def _bar_color(score: float, max_score: float) -> str:
    ratio = score / max_score if max_score else 0
    if ratio >= 0.85:
        return "green"
    elif ratio >= 0.6:
        return "yellow"
    return "red"


def print_scan_result(env: EnvSnapshot, tools: list[Tool], *, no_color: bool = False) -> None:
    console = Console(no_color=no_color, highlight=False)

    console.print()
    console.print(Rule(f"[bold cyan]agentscore[/bold cyan]  {t('terminal_header').split('  ', 1)[-1]}", style="dim"))
    console.print(
        f"  Claude [dim]{env.claude_version}[/dim]   "
        f"[dim]{env.scan_timestamp[:19].replace('T', ' ')} UTC[/dim]",
        highlight=False,
    )
    console.print()

    if not tools:
        console.print(f"  [yellow]{t('terminal_no_tools')}[/yellow]")
        return

    _print_tools_table(console, tools)


def print_score_result(result: ScanResult, *, tools: list[Tool] | None = None, no_color: bool = False) -> None:
    console = Console(no_color=no_color, highlight=False)
    grade = result.grade
    color = GRADE_COLOR.get(grade, "white")

    score_text = Text()
    score_text.append(f" {grade} ", style=f"bold {color} on default")
    score_text.append(f"  {result.total_score:.1f}점", style="bold white")
    score_text.append(f"  ·  {result.profile.role}", style="dim")

    console.print(
        Panel(score_text, box=box.DOUBLE_EDGE, border_style=color, padding=(0, 2), expand=False)
    )
    console.print()

    for dim, label in DIMENSION_LABELS.items():
        score = result.scores.get(dim, 0.0)
        max_s = DIMENSION_MAX[dim]
        bar = _bar(score, max_s)
        bc = _bar_color(score, max_s)
        check = "[green]✓[/green]" if score >= max_s else " "

        console.print(
            f"  {label}  [{bc}]{bar}[/{bc}]  "
            f"[bold]{score:4.1f}[/bold][dim]/{max_s}[/dim]  {check}",
            highlight=False,
        )

    console.print()

    if result.issues:
        console.print(Rule(t("terminal_improvements"), style="dim", align="left"))
        severity_icon = {"error": "[red]✗[/red]", "warning": "[yellow]△[/yellow]", "info": "[dim]ℹ[/dim]"}
        for issue in result.issues[:5]:
            icon = severity_icon.get(issue.severity, "·")
            console.print(f"  {icon}  [dim]{issue.dimension}[/dim]  {issue.message}", highlight=False, soft_wrap=True)
            if issue.recommendation:
                console.print(f"       [dim]→ {issue.recommendation}[/dim]", highlight=False, soft_wrap=True)
        console.print()

    tips = _generate_tips(result, tools=tools)
    if tips:
        console.print(Rule(t("terminal_tips"), style="dim", align="left"))
        for i, tip in enumerate(tips, 1):
            console.print(f"  [cyan]{i}.[/cyan]  {tip}", highlight=False, soft_wrap=True)
        console.print()


def _print_tools_table(console: Console, tools: list[Tool]) -> None:
    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold dim",
        pad_edge=False,
        show_edge=False,
    )
    table.add_column(t("col_tool"), min_width=26)
    table.add_column(t("col_category"), min_width=14)
    table.add_column(t("col_cost"), justify="center", min_width=8)
    table.add_column(t("col_priority"), justify="center", min_width=10)
    table.add_column("", justify="center", min_width=4)

    for tool in tools:
        cost_cell = f"{COST_EMOJI.get(tool.context_cost, '❓')} {COST_LABEL.get(tool.context_cost, tool.context_cost)}"
        priority_cell = f"{PRIORITY_EMOJI.get(tool.config_priority, '?')} {tool.config_priority}"
        reg = "[dim]✓[/dim]" if tool.in_registry else "[dim]?[/dim]"

        name_style = "bold" if tool.in_registry else "dim"
        table.add_row(
            f"[{name_style}]{tool.display_name}[/{name_style}]",
            f"[dim]{tool.category}[/dim]",
            cost_cell,
            priority_cell,
            reg,
        )

    console.print(table)
    console.print(f"  [dim]{t('terminal_tool_count', n=len(tools)).strip()}[/dim]")
    console.print()
