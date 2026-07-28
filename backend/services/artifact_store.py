"""Local expiring artifact store with strict identifier and filename checks."""

import re
import shutil
import time
import uuid
from pathlib import Path

from core.config import settings

ARTIFACT_ROOT = Path(__file__).resolve().parent.parent / "artifacts"
_ARTIFACT_ID = re.compile(r"^[0-9a-f]{32}$")
_ALLOWED_FILENAMES = {"resume.tex", "resume.pdf"}


def save_resume_artifacts(tex_path: Path, pdf_path: Path | None) -> str:
    cleanup_expired_artifacts()
    artifact_id = uuid.uuid4().hex
    destination = ARTIFACT_ROOT / artifact_id
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(tex_path, destination / "resume.tex")
    if pdf_path and pdf_path.exists():
        shutil.copy2(pdf_path, destination / "resume.pdf")
    return artifact_id


def resolve_artifact(artifact_id: str, filename: str) -> Path | None:
    if not _ARTIFACT_ID.fullmatch(artifact_id):
        return None
    if filename not in _ALLOWED_FILENAMES:
        return None
    candidate = (ARTIFACT_ROOT / artifact_id / filename).resolve()
    root = ARTIFACT_ROOT.resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def cleanup_expired_artifacts() -> None:
    if not ARTIFACT_ROOT.exists():
        return
    cutoff = time.time() - settings.CREATOR_ARTIFACT_TTL_HOURS * 3600
    for directory in ARTIFACT_ROOT.iterdir():
        if (
            directory.is_dir()
            and _ARTIFACT_ID.fullmatch(directory.name)
            and directory.stat().st_mtime < cutoff
        ):
            shutil.rmtree(directory, ignore_errors=True)
