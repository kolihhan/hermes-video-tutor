from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from threading import RLock
from typing import Iterable

from .contracts import Evidence, EvidenceKind
from .final_answer import FinalAnswerFormatError, extract_citation_ids, parse_final_answer as _parse_final_answer


class CitationError(ValueError):
    pass


def parse_final_answer(text: str) -> str:
    try:
        return _parse_final_answer(text)
    except FinalAnswerFormatError as exc:
        raise CitationError(str(exc)) from exc


class EvidenceStore:
    def __init__(self, session_dir: str | Path) -> None:
        self.session_dir = Path(session_dir).resolve()
        self.path = self.session_dir / "evidence.jsonl"
        self._lock = RLock()

    def add(
        self,
        *,
        kind: EvidenceKind,
        start_s: float,
        end_s: float,
        text: str,
        media_paths: tuple[str, ...] = (),
    ) -> Evidence:
        with self._lock:
            existing = self.all()
            evidence = Evidence(
                evidence_id=f"E{len(existing) + 1}",
                kind=kind,
                start_s=float(start_s),
                end_s=float(end_s),
                text=str(text),
                media_paths=tuple(str(p) for p in media_paths),
            )
            self.session_dir.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(asdict(evidence), ensure_ascii=False) + "\n")
                fh.flush()
            return evidence

    def all(self) -> tuple[Evidence, ...]:
        if not self.path.is_file():
            return ()
        records: list[Evidence] = []
        for index, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                records.append(
                    Evidence(
                        evidence_id=str(row["evidence_id"]),
                        kind=row["kind"],
                        start_s=float(row["start_s"]),
                        end_s=float(row["end_s"]),
                        text=str(row["text"]),
                        media_paths=tuple(str(p) for p in row.get("media_paths", ())),
                    )
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid evidence record at line {index}") from exc
        return tuple(records)


def validate_citations(
    text: str,
    evidence: Iterable[Evidence],
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    cited = extract_citation_ids(text)
    if not cited and not allow_empty:
        raise CitationError("answer must cite evidence")
    known = {item.evidence_id for item in evidence}
    unknown = [item for item in cited if item not in known]
    if unknown:
        raise CitationError("unknown evidence citation(s): " + ", ".join(unknown))
    return cited
