from __future__ import annotations

import os
from pathlib import Path
from threading import RLock

from .tool_runtime import VideoToolRuntime

_RUNTIME: VideoToolRuntime | None = None
_KEY: tuple[str, str] | None = None
_LOCK = RLock()


def runtime_from_environment() -> VideoToolRuntime:
    global _RUNTIME, _KEY
    course = os.environ.get("VIDEO_TUTOR_COURSE", "").strip()
    session = os.environ.get("VIDEO_TUTOR_SESSION", "").strip()
    if not course or not session:
        raise RuntimeError("VIDEO_TUTOR_COURSE and VIDEO_TUTOR_SESSION must be configured")
    key = (str(Path(course).resolve()), str(Path(session).resolve()))
    with _LOCK:
        if _RUNTIME is None or _KEY != key:
            _RUNTIME = VideoToolRuntime(course_manifest=key[0], session_dir=key[1])
            _KEY = key
        return _RUNTIME


def execute_tool(name: str, arguments: dict):
    return runtime_from_environment().execute(name, arguments)
