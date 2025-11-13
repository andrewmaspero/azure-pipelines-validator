"""Pretty console output for validation results."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence, TypeAlias

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import (
    FileValidationResult,
    PreviewFinding,
    SchemaFinding,
    ValidationSummary,
    YamllintFinding,
)

CheckExtractor: TypeAlias = Callable[[FileValidationResult], Sequence[object]]


class Reporter:
    """Renders a concise summary using Rich tables."""

    def __init__(self, repo_root: Path, console: Console | None = None) -> None:
        self._repo_root = repo_root
        self._console = console or Console()

    def display(self, summary: ValidationSummary) -> None:
        checks = _active_checks(summary)
        table = Table(
            title="Azure Pipelines YAML validation",
            expand=True,
            box=box.ROUNDED,
            header_style="bold white",
            highlight=True,
        )
        table.add_column("File", overflow="fold")
        for label, _ in checks:
            table.add_column(label)

        for result in summary.results:
            row: list[Text | str] = [self._format_path(result.path)]
            for _, extractor in checks:
                findings = extractor(result)
                row.append(_status_cell(findings))
            table.add_row(*row)

        self._console.print(table)
        status_style = "bold green" if summary.success else "bold red"
        summary_line = (
            f"Validated {summary.total_files} file(s). Failures: {summary.failing_files}."
        )
        self._console.print(Text(summary_line, style=status_style))

        panels = _build_error_panels(summary, checks, self._format_path)
        if panels:
            self._console.print()
            self._console.print(Columns(panels, expand=True))

    def _format_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self._repo_root))
        except ValueError:
            return str(path)


def _active_checks(summary: ValidationSummary) -> list[tuple[str, CheckExtractor]]:
    checks: list[tuple[str, CheckExtractor]] = []
    if summary.options.include_lint:
        checks.append(("yamllint", lambda r: r.yamllint))
    if summary.options.include_schema:
        checks.append(("schema", lambda r: r.schema))
    if summary.options.include_preview:
        checks.append(("preview", lambda r: r.preview))
    return checks


def _status_cell(findings: Sequence[object]) -> Text:
    if not findings:
        return Text("pass", style="bold green")
    return Text("fail", style="bold red")


def _build_error_panels(
    summary: ValidationSummary,
    checks: Sequence[tuple[str, CheckExtractor]],
    path_formatter: Callable[[Path], str],
) -> list[Panel]:
    panels: list[Panel] = []
    for result in summary.results:
        for label, extractor in checks:
            findings = extractor(result)
            if not findings:
                continue
            panels.append(
                Panel(
                    _format_findings(findings),
                    title=f"{path_formatter(result.path)} • {label}",
                    box=box.ROUNDED,
                    border_style="red",
                )
            )
    return panels


def _format_findings(findings: Sequence[object]) -> Text:
    text = Text()
    for index, finding in enumerate(findings, start=1):
        message = _finding_message(finding)
        text.append(f"{index}. ", style="bold white")
        text.append(message)
        if index < len(findings):
            text.append("\n")
    return text


def _finding_message(finding: object) -> str:
    if isinstance(finding, YamllintFinding):
        return f"L{finding.line} C{finding.column}: {finding.message}"
    if isinstance(finding, SchemaFinding):
        return f"{finding.json_pointer}: {finding.message}"
    if isinstance(finding, PreviewFinding):
        level = f"[{finding.level}] " if finding.level else ""
        return f"{level}{finding.message}"
    return str(getattr(finding, "message", finding))
