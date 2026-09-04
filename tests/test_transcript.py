import json
from pathlib import Path

from video_tutor.transcript import TranscriptIndex, load_transcript


def _write_transcript(path: Path) -> None:
    path.write_text(json.dumps([
        {"segment_id":"s1","start_s":0,"end_s":8,"text":"Today we introduce the three-stage pipeline."},
        {"segment_id":"s2","start_s":8,"end_s":16,"text":"First retrieve evidence, then reason, then answer."},
        {"segment_id":"s3","start_s":16,"end_s":24,"text":"This diagram shows the architecture on screen."},
    ]), encoding="utf-8")


def test_search_transcript_ranks_relevant_segment(tmp_path):
    path = tmp_path / "transcript.json"
    _write_transcript(path)
    index = TranscriptIndex(load_transcript(path))
    hits = index.search("three stage pipeline", top_k=2)
    assert hits[0].segment.segment_id == "s1"
    assert hits[0].score > 0


def test_expand_context_returns_neighboring_segments(tmp_path):
    path = tmp_path / "transcript.json"
    _write_transcript(path)
    index = TranscriptIndex(load_transcript(path))
    window = index.expand_context("s2", before_s=10, after_s=10)
    assert [s.segment_id for s in window] == ["s1", "s2", "s3"]
