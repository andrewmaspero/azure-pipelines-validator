from __future__ import annotations

from pathlib import Path

from rich.console import Console

from azure_pipelines_validator.models import (
    FileValidationResult,
    PreviewFinding,
    SchemaFinding,
    ValidationOptions,
    ValidationSummary,
    YamllintFinding,
)
from azure_pipelines_validator.reporter import Reporter


def test_reporter_renders_summary(tmp_path: Path) -> None:
    console = Console(record=True)
    file_path = tmp_path / "pipeline.yml"
    file_path.write_text("trigger: none", encoding="utf-8")

    summary = ValidationSummary(
        results=(
            FileValidationResult(
                path=file_path,
                yamllint=tuple(),
                schema=tuple(),
                preview=tuple(),
                final_yaml="trigger: none",
            ),
            FileValidationResult(
                path=file_path,
                yamllint=(
                    YamllintFinding(
                        path=file_path,
                        line=1,
                        column=1,
                        level="error",
                        message="indent",
                    ),
                ),
                schema=(
                    SchemaFinding(
                        path=file_path,
                        json_pointer="/trigger",
                        message="missing",
                    ),
                ),
                preview=(
                    PreviewFinding(
                        path=file_path,
                        message="preview error",
                        level="error",
                    ),
                ),
                final_yaml=None,
            ),
        ),
        options=ValidationOptions(),
    )

    reporter = Reporter(repo_root=tmp_path, console=console)
    reporter.display(summary)

    output = console.export_text()
    assert "Failures: 1" in output
    assert "pipeline.yml" in output
    assert "yamllint" in output
    assert "schema" in output
    assert "preview" in output
    assert "L1 C1" in output  # yamllint finding rendered in panel
    assert "/trigger" in output  # schema finding rendered in panel
    assert "preview error" in output


def test_reporter_hides_skipped_checks(tmp_path: Path) -> None:
    console = Console(record=True)
    file_path = tmp_path / "pipeline.yml"
    file_path.write_text("trigger: none", encoding="utf-8")

    summary = ValidationSummary(
        results=(
            FileValidationResult(
                path=file_path,
                yamllint=tuple(),
                schema=(
                    SchemaFinding(
                        path=file_path,
                        json_pointer="/trigger",
                        message="invalid",
                    ),
                ),
                preview=tuple(),
                final_yaml=None,
            ),
        ),
        options=ValidationOptions(include_lint=False, include_schema=True, include_preview=False),
    )

    reporter = Reporter(repo_root=tmp_path, console=console)
    reporter.display(summary)

    output = console.export_text()
    assert "schema" in output
    assert "yamllint" not in output
    assert "preview" not in output
    assert "/trigger" in output  # Panel details
