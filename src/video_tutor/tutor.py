from __future__ import annotations

import json
from pathlib import Path
import uuid

from .activity import ActivityStore
from .contracts import TutorAnswer
from .evidence import CitationError, EvidenceStore, validate_citations
from .final_answer import FinalAnswerFormatError, parse_final_answer
from .hermes_runtime import AgentRuntime, RuntimeRequest

_ABSTENTION = "Insufficient evidence to determine the answer from this lecture."


class TutorService:
    def __init__(self, *, runtime: AgentRuntime, session_root: str | Path) -> None:
        self.runtime = runtime
        self.session_root = Path(session_root).resolve()

    def ask(self, *, question: str, course_manifest: str | Path) -> TutorAnswer:
        if not question.strip():
            raise ValueError("question must not be empty")
        manifest = Path(course_manifest).resolve()
        session_dir = self.session_root / uuid.uuid4().hex
        session_dir.mkdir(parents=True, exist_ok=False)
        raw = self.runtime.ask(RuntimeRequest(
            question=question,
            course_manifest=manifest,
            session_dir=session_dir,
        )).strip()
        evidence = EvidenceStore(session_dir).all()
        activity = ActivityStore(session_dir).all()
        usage_path = session_dir / "hermes-usage.json"
        usage = json.loads(usage_path.read_text(encoding="utf-8")) if usage_path.is_file() else {}
        if not isinstance(usage, dict):
            raise ValueError("Hermes usage report must be a JSON object")
        if raw == "INSUFFICIENT_EVIDENCE":
            return TutorAnswer(
                text=_ABSTENTION,
                status="insufficient_evidence",
                evidence=evidence,
                activity=activity,
                usage=usage,
                raw_model_answer=raw,
            )
        try:
            parse_final_answer(raw)
        except FinalAnswerFormatError:
            return TutorAnswer(
                text=_ABSTENTION,
                status="insufficient_evidence",
                evidence=evidence,
                activity=activity,
                usage=usage,
                raw_model_answer=raw,
                rejection_reason="invalid_final_format",
            )
        try:
            validate_citations(raw, evidence)
        except CitationError:
            return TutorAnswer(
                text=_ABSTENTION,
                status="insufficient_evidence",
                evidence=evidence,
                activity=activity,
                usage=usage,
                raw_model_answer=raw,
                rejection_reason="invalid_citation",
            )
        return TutorAnswer(
            text=raw, status="answered", evidence=evidence, activity=activity, usage=usage,
            raw_model_answer=raw, rejection_reason=None,
        )
