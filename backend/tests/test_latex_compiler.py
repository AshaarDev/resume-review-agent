"""Restricted LaTeX compiler behavior tests."""

from types import SimpleNamespace

from core.creator_schemas import CompilationStatus
from services import latex_compiler


def test_compiler_reports_source_only_when_pdflatex_is_missing(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(latex_compiler.shutil, "which", lambda _: None)
    tex_path = tmp_path / "resume.tex"
    tex_path.write_text("test", encoding="utf-8")

    result = latex_compiler.compile_latex(tex_path)

    assert result.status == CompilationStatus.SOURCE_ONLY
    assert result.error_code == "LATEX_COMPILER_UNAVAILABLE"


def test_compiler_disables_shell_escape(monkeypatch, tmp_path):
    calls = []
    tex_path = tmp_path / "resume.tex"
    tex_path.write_text("test", encoding="utf-8")
    tex_path.with_suffix(".pdf").write_bytes(b"%PDF")
    monkeypatch.setattr(
        latex_compiler.shutil, "which", lambda _: "/usr/bin/pdflatex"
    )

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(latex_compiler.subprocess, "run", fake_run)

    result = latex_compiler.compile_latex(tex_path)

    assert result.status == CompilationStatus.COMPILED
    assert "-no-shell-escape" in calls[0][0]
    assert calls[0][1]["cwd"] == tmp_path
    assert calls[0][1]["check"] is False
