from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

EvidenceKind = Literal["transcript", "frame", "clip"]


@dataclass(frozen=True)
class Course:
    course_id: str
    title: str
    video_path: Path
    transcript_path: Path


@dataclass(frozen=True)
class TranscriptSegment:
    segment_id: str
    start_s: float
    end_s: float
    text: str


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    kind: EvidenceKind
    start_s: float
    end_s: float
    text: str
    media_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActivityEvent:
    tool: str
    summary: str
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TutorAnswer:
    text: str
    status: Literal["answered", "insufficient_evidence"]
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    activity: tuple[ActivityEvent, ...] = field(default_factory=tuple)
    usage: dict[str, object] = field(default_factory=dict)
    raw_model_answer: str = ""
    rejection_reason: str | None = None
