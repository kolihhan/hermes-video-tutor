from __future__ import annotations

from pathlib import Path

from .hermes_runtime import HermesCliRuntime
from .tutor import TutorService


def build_tutor_service(*, repo_root: str | Path | None = None) -> TutorService:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    run_root = root / ".run"
    return TutorService(
        runtime=HermesCliRuntime(repo_root=root, hermes_home=run_root / "hermes-home"),
        session_root=run_root / "sessions",
    )
