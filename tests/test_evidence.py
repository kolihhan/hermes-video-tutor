from pathlib import Path

import pytest

from video_tutor.evidence import EvidenceStore, CitationError, validate_citations


def test_evidence_store_assigns_stable_session_ids_and_persists(tmp_path):
    store = EvidenceStore(tmp_path)
    e1 = store.add(kind="transcript", start_s=2, end_s=4, text="hello")
    e2 = store.add(kind="frame", start_s=5, end_s=5, text="frame", media_paths=("frame.jpg",))
    assert (e1.evidence_id, e2.evidence_id) == ("E1", "E2")
    reloaded = EvidenceStore(tmp_path).all()
    assert [e.evidence_id for e in reloaded] == ["E1", "E2"]


def test_citation_validator_rejects_unknown_ids(tmp_path):
    store = EvidenceStore(tmp_path)
    store.add(kind="transcript", start_s=0, end_s=1, text="x")
    assert validate_citations("Answer [E1]", store.all()) == ("E1",)
    with pytest.raises(CitationError, match="unknown evidence"):
        validate_citations("Answer [E2]", store.all())


def test_no_citation_is_allowed_for_explicit_abstention(tmp_path):
    assert validate_citations("Insufficient evidence to determine this.", (), allow_empty=True) == ()
