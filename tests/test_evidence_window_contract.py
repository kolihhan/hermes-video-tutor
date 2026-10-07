from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))


def test_visual_window_requires_visual_evidence_inside_expected_window():
    from evaluation.evaluate import evaluate_prediction

    gold = {
        "case_id": "q-visual-window",
        "reference_answer": "blue",
        "accepted_aliases": [],
        "required_modality": "visual",
        "expected_evidence_window": [3.0, 6.0],
    }
    prediction = {
        "case_id": "q-visual-window",
        "answer": "FINAL: blue [E1] [E2]",
        "evidence": [
            {"evidence_id": "E1", "kind": "frame", "start_s": 20.0, "end_s": 20.0},
            {"evidence_id": "E2", "kind": "transcript", "start_s": 4.0, "end_s": 5.0},
        ],
        "tool_calls": ["inspect_frame", "search_transcript"],
    }

    result = evaluate_prediction(prediction, gold)

    assert result.citation_valid is True
    assert result.modality_correct is True
    assert result.evidence_window_correct is False
    assert result.passed is False
