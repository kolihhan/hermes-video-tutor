from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Iterable

from .contracts import TranscriptSegment

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def load_transcript(path: str | Path) -> tuple[TranscriptSegment, ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("transcript must be a JSON list")
    segments: list[TranscriptSegment] = []
    seen: set[str] = set()
    last_start = -1.0
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError("transcript entries must be objects")
        segment = TranscriptSegment(
            segment_id=str(row["segment_id"]),
            start_s=float(row["start_s"]),
            end_s=float(row["end_s"]),
            text=str(row["text"]),
        )
        if segment.segment_id in seen:
            raise ValueError(f"duplicate transcript segment_id: {segment.segment_id}")
        if segment.start_s < 0 or segment.end_s < segment.start_s:
            raise ValueError(f"invalid transcript time range: {segment.segment_id}")
        if segment.start_s < last_start:
            raise ValueError("transcript segments must be sorted by start_s")
        seen.add(segment.segment_id)
        last_start = segment.start_s
        segments.append(segment)
    return tuple(segments)


@dataclass(frozen=True)
class TranscriptHit:
    segment: TranscriptSegment
    score: float


class TranscriptIndex:
    def __init__(self, segments: Iterable[TranscriptSegment]) -> None:
        self.segments = tuple(segments)
        if not self.segments:
            raise ValueError("transcript is empty")
        self._by_id = {s.segment_id: s for s in self.segments}
        self._docs = [_tokens(s.text) for s in self.segments]
        self._df: Counter[str] = Counter()
        for doc in self._docs:
            self._df.update(set(doc))
        self._avg_len = sum(map(len, self._docs)) / len(self._docs)

    def search(self, query: str, *, top_k: int = 5) -> tuple[TranscriptHit, ...]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        query_tokens = _tokens(query)
        if not query_tokens:
            return ()
        n = len(self._docs)
        scores: list[TranscriptHit] = []
        for segment, doc in zip(self.segments, self._docs):
            tf = Counter(doc)
            score = 0.0
            dl = len(doc) or 1
            for token in query_tokens:
                freq = tf.get(token, 0)
                if not freq:
                    continue
                df = self._df[token]
                idf = math.log(1.0 + (n - df + 0.5) / (df + 0.5))
                k1, b = 1.5, 0.75
                score += idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / self._avg_len))
            if score > 0:
                scores.append(TranscriptHit(segment=segment, score=score))
        scores.sort(key=lambda hit: (-hit.score, hit.segment.start_s, hit.segment.segment_id))
        return tuple(scores[:top_k])

    def expand_context(
        self,
        segment_id: str,
        *,
        before_s: float = 30.0,
        after_s: float = 30.0,
    ) -> tuple[TranscriptSegment, ...]:
        if before_s < 0 or after_s < 0:
            raise ValueError("context radii must be non-negative")
        center = self._by_id.get(segment_id)
        if center is None:
            raise KeyError(f"unknown transcript segment: {segment_id}")
        start = center.start_s - before_s
        end = center.end_s + after_s
        return tuple(s for s in self.segments if s.end_s >= start and s.start_s <= end)
