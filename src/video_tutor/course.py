from __future__ import annotations

import json
from pathlib import Path

from .contracts import Course

_ALLOWED_KEYS = {"course_id", "title", "video_path", "transcript_path"}


def load_course_manifest(path: str | Path) -> Course:
    manifest = Path(path).resolve()
    row = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(row, dict):
        raise ValueError("course manifest must be an object")
    unexpected = sorted(set(row) - _ALLOWED_KEYS)
    if unexpected:
        raise ValueError("unexpected course metadata: " + ", ".join(unexpected))
    missing = sorted(_ALLOWED_KEYS - set(row))
    if missing:
        raise ValueError("missing course metadata: " + ", ".join(missing))
    root = manifest.parent
    video = (root / str(row["video_path"])).resolve()
    transcript = (root / str(row["transcript_path"])).resolve()
    for candidate, label in ((video, "video"), (transcript, "transcript")):
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"{label} path escapes course directory") from exc
        if not candidate.is_file():
            raise ValueError(f"{label} file does not exist: {candidate.name}")
    return Course(
        course_id=str(row["course_id"]),
        title=str(row["title"]),
        video_path=video,
        transcript_path=transcript,
    )
