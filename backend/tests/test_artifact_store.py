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


def test_word_artifact_is_saved_and_downloaded(monkeypatch, tmp_path):
    from main import app
    from fastapi.testclient import TestClient
    monkeypatch.setattr(artifact_store, "ARTIFACT_ROOT", tmp_path / "artifacts")
    tex = tmp_path / "resume.tex"
    word = tmp_path / "resume.docx"
    tex.write_text("test", encoding="utf-8")
    word.write_bytes(b"PK-word-test")
    artifact_id = artifact_store.save_resume_artifacts(tex, None, word)
    assert artifact_store.resolve_artifact(artifact_id, "resume.docx").read_bytes() == b"PK-word-test"
    response = TestClient(app).get(f"/api/artifacts/{artifact_id}/resume.docx")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert "attachment" in response.headers["content-disposition"]
