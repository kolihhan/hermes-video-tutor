from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from threading import RLock

from .contracts import ActivityEvent


class ActivityStore:
    def __init__(self, session_dir: str | Path) -> None:
        self.session_dir = Path(session_dir).resolve()
        self.path = self.session_dir / "activity.jsonl"
        self._lock = RLock()

    def add(self, event: ActivityEvent) -> None:
        with self._lock:
            self.session_dir.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
                fh.flush()

    def all(self) -> tuple[ActivityEvent, ...]:
        if not self.path.is_file():
            return ()
        out: list[ActivityEvent] = []
        for index, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                out.append(ActivityEvent(
                    tool=str(row["tool"]),
                    summary=str(row["summary"]),
                    evidence_ids=tuple(str(x) for x in row.get("evidence_ids", ())),
                ))
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid activity record at line {index}") from exc
        return tuple(out)
