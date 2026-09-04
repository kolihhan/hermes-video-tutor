import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))


def test_inference_cases_are_physically_gold_free():
    rows = json.loads((ROOT / "evaluation" / "inference_cases.json").read_text(encoding="utf-8"))
    forbidden = {"reference_answer", "required_modality", "expected_evidence_window", "gold", "annotation", "caption"}
    for row in rows:
        assert forbidden.isdisjoint(row)
        assert set(row) == {"case_id", "question", "course"}


def test_wrong_answer_with_valid_citation_is_not_semantically_correct():
    from evaluation.evaluate import evaluate_prediction

    gold = {
        "case_id": "q-visual",
        "reference_answer": "blue",
        "required_modality": "visual",
        "expected_evidence_window": [3.0, 6.0],
    }
    prediction = {
        "case_id": "q-visual",
        "answer": "FINAL: green [E1]",
        "evidence": [{"evidence_id": "E1", "kind": "frame", "start_s": 4.0, "end_s": 4.0}],
        "tool_calls": ["inspect_frame"],
    }
    result = evaluate_prediction(prediction, gold)
    assert result.citation_valid is True
    assert result.modality_correct is True
    assert result.answer_correct is False
    assert result.passed is False


def test_visual_case_requires_cited_visual_evidence_not_merely_any_citation():
    from evaluation.evaluate import evaluate_prediction

    gold = {
        "case_id": "q-visual",
        "reference_answer": "blue",
        "required_modality": "visual",
        "expected_evidence_window": [3.0, 6.0],
    }
    prediction = {
        "case_id": "q-visual",
        "answer": "FINAL: blue [E1]",
        "evidence": [{"evidence_id": "E1", "kind": "transcript", "start_s": 3.0, "end_s": 5.0}],
        "tool_calls": ["search_transcript"],
    }
    result = evaluate_prediction(prediction, gold)
    assert result.answer_correct is True
    assert result.citation_valid is True
    assert result.modality_correct is False
    assert result.passed is False


def test_correct_visual_answer_with_cited_frame_passes():
    from evaluation.evaluate import evaluate_prediction

    gold = {
        "case_id": "q-visual",
        "reference_answer": "blue",
        "required_modality": "visual",
        "expected_evidence_window": [3.0, 6.0],
    }
    prediction = {
        "case_id": "q-visual",
        "answer": "FINAL: blue [E2]",
        "evidence": [{"evidence_id": "E2", "kind": "frame", "start_s": 4.0, "end_s": 4.0}],
        "tool_calls": ["inspect_frame"],
    }
    result = evaluate_prediction(prediction, gold)
    assert result.answer_correct
    assert result.citation_valid
    assert result.modality_correct
    assert result.evidence_window_correct
    assert result.passed


def test_evaluator_accepts_only_canonical_answers_or_explicit_aliases():
    from evaluation.evaluate import evaluate_prediction

    gold = {"case_id": "q", "reference_answer": "five minutes", "accepted_aliases": ["5 minutes", "5 min"],
            "required_modality": "transcript", "expected_evidence_window": [0, 5]}
    evidence = [{"evidence_id": "E1", "kind": "transcript", "start_s": 1, "end_s": 2}]
    assert evaluate_prediction({"case_id": "q", "answer": "FINAL: 5 min [E1]", "evidence": evidence}, gold).answer_correct
    assert not evaluate_prediction({"case_id": "q", "answer": "FINAL: five minutes later [E1]", "evidence": evidence}, gold).answer_correct


def test_frozen_live_set_has_physically_separate_twelve_runtime_and_gold_rows():
    runtime = json.loads((ROOT / "evaluation" / "live_inference_cases.json").read_text(encoding="utf-8"))
    gold = json.loads((ROOT / "evaluation" / "live_gold_labels.json").read_text(encoding="utf-8"))
    assert len(runtime) == len(gold) == 12
    assert all(set(row) == {"case_id", "question", "course"} for row in runtime)
    assert all({"reference_answer", "accepted_aliases", "required_modality", "expected_evidence_window"}.issubset(row) for row in gold)
    assert {row["case_id"] for row in runtime} == {row["case_id"] for row in gold}


def test_frozen_live_aliases_cover_the_explicit_and_numeric_variants():
    from evaluation.evaluate import evaluate_prediction

    gold = {
        row["case_id"]: row
        for row in json.loads((ROOT / "evaluation" / "live_gold_labels.json").read_text(encoding="utf-8"))
    }
    examples = {
        "p3-t02": "FINAL: collect, compare, and decide [E1]",
        "p3-t03": "FINAL: five min [E1]",
        "p3-t05": "FINAL: 2 [E1]",
    }
    for case_id, answer in examples.items():
        start, end = gold[case_id]["expected_evidence_window"]
        prediction = {
            "case_id": case_id,
            "answer": answer,
            "evidence": [{"evidence_id": "E1", "kind": "transcript", "start_s": start, "end_s": end}],
        }
        assert evaluate_prediction(prediction, gold[case_id]).answer_correct


def test_v2_evaluator_extracts_only_final_short_answer_before_citations():
    from evaluation.evaluate import evaluate_prediction
    gold = {
        "case_id": "q", "reference_answer": "orion", "accepted_aliases": [],
        "required_modality": "transcript", "expected_evidence_window": [0, 5],
    }
    evidence = [{"evidence_id": "E1", "kind": "transcript", "start_s": 1, "end_s": 2}]
    good = {"case_id": "q", "answer": "FINAL: Orion [E1]", "evidence": evidence}
    prose = {"case_id": "q", "answer": "The project codename is Orion [E1].", "evidence": evidence}
    wrong = {"case_id": "q", "answer": "FINAL: Atlas [E1]", "evidence": evidence}
    assert evaluate_prediction(good, gold).answer_correct is True
    assert evaluate_prediction(prose, gold).answer_correct is False
    assert evaluate_prediction(wrong, gold).answer_correct is False
