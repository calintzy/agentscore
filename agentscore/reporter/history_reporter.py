from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich import box

from agentscore.history.diff import DiffResult, DIMENSION_LABELS

GRADE_STYLE = {
    "S": "bright_cyan", "A": "green", "B": "yellow", "C": "dark_orange", "D": "red",
}


def print_history(records: list[dict], *, no_color: bool = False) -> None:
    console = Console(no_color=no_color, highlight=False)

    if not records:
        console.print("[dim]히스토리가 없습니다. agentscore를 먼저 실행하세요.[/dim]")
        return

    console.print()
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold", pad_edge=False)
    table.add_column("날짜/시각", min_width=20)
    table.add_column("등급", justify="center", min_width=6)
    table.add_column("점수", justify="right", min_width=8)
    table.add_column("프로필", min_width=12)
    table.add_column("도구 수", justify="right", min_width=8)
    table.add_column("이슈 수", justify="right", min_width=8)

    for rec in records:
        grade = rec.get("grade", "?")
        style = GRADE_STYLE.get(grade, "")
        ts = rec.get("timestamp", rec.get("_file", "?"))[:19].replace("T", " ")
        table.add_row(
            ts,
            f"[{style}]{grade}[/{style}]",
            f"{rec.get('total_score', 0):.1f}",
            rec.get("profile", {}).get("role", "?"),
            str(rec.get("tool_count", 0)),
            str(rec.get("issues_count", 0)),
        )

    console.print(table)
    console.print()


def print_diff(diff: DiffResult, *, no_color: bool = False) -> None:
    console = Console(no_color=no_color, highlight=False)

    before_ts = diff.before.get("timestamp", "?")[:19].replace("T", " ")
    after_ts = diff.after.get("timestamp", "?")[:19].replace("T", " ")

    console.print()
    console.print(f"[bold]비교[/bold]: {before_ts} → {after_ts}", highlight=False)
    console.print()

    delta_style = "green" if diff.total_delta >= 0 else "red"
    before_score = diff.before.get("total_score", 0)
    after_score = diff.after.get("total_score", 0)
    console.print(
        f"총점:  {before_score:.1f} → [{delta_style}]{after_score:.1f} ({diff.total_delta:+.1f})[/{delta_style}]",
        highlight=False,
    )

    if diff.tool_count_delta != 0:
        sign = "+" if diff.tool_count_delta > 0 else ""
        console.print(f"도구 수: {diff.before.get('tool_count', 0)} → {diff.after.get('tool_count', 0)} ({sign}{diff.tool_count_delta})", highlight=False)

    console.print()

    table = Table(box=box.SIMPLE, show_header=True, header_style="dim", pad_edge=False)
    table.add_column("차원", min_width=20)
    table.add_column("이전", justify="right", min_width=6)
    table.add_column("현재", justify="right", min_width=6)
    table.add_column("변화", justify="right", min_width=7)

    before_scores = diff.before.get("scores", {})
    after_scores = diff.after.get("scores", {})

    for dim, label in DIMENSION_LABELS.items():
        before_v = before_scores.get(dim, 0.0)
        after_v = after_scores.get(dim, 0.0)
        delta = diff.dimension_deltas.get(dim, 0.0)

        if abs(delta) < 0.05:
            delta_cell = "[dim]  —[/dim]"
        elif delta > 0:
            delta_cell = f"[green]+{delta:.1f}[/green]"
        else:
            delta_cell = f"[red]{delta:.1f}[/red]"

        table.add_row(label, f"{before_v:.1f}", f"{after_v:.1f}", delta_cell)

    console.print(table)
    console.print()
