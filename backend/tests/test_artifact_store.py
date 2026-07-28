"""Generated artifact path isolation tests."""

from pathlib import Path

from services import artifact_store


def test_artifact_store_restricts_ids_and_filenames(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(artifact_store, "ARTIFACT_ROOT", tmp_path)
    artifact_id = "a" * 32
    directory = tmp_path / artifact_id
    directory.mkdir()
    (directory / "resume.tex").write_text("resume", encoding="utf-8")

    assert artifact_store.resolve_artifact(
        artifact_id, "resume.tex"
    ) == (directory / "resume.tex").resolve()
    assert artifact_store.resolve_artifact("../secret", "resume.tex") is None
    assert artifact_store.resolve_artifact(artifact_id, "../secret") is None
    assert artifact_store.resolve_artifact(artifact_id, "other.tex") is None
