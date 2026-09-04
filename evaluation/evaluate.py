from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable

from video_tutor.final_answer import FinalAnswerFormatError, parse_final_answer

_CITATION_RE = re.compile(r"\[(E\d+)\]", re.IGNORECASE)
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    answer_correct: bool
    citation_valid: bool
    modality_correct: bool
    evidence_window_correct: bool
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_answer(text: str) -> str:
    without_citations = _CITATION_RE.sub(" ", text.lower())
    return " ".join(_NON_WORD_RE.sub(" ", without_citations).split())


def _cited_evidence(prediction: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    cited_ids = tuple(dict.fromkeys(item.upper() for item in _CITATION_RE.findall(str(prediction.get("answer", "")))))
    evidence = prediction.get("evidence", [])
    if not isinstance(evidence, list):
        return ()
    by_id = {
        str(row.get("evidence_id")): row
        for row in evidence
        if isinstance(row, dict) and row.get("evidence_id") is not None
    }
    if not cited_ids or any(eid not in by_id for eid in cited_ids):
        return ()
    return tuple(by_id[eid] for eid in cited_ids)


def _modality_matches(required: str, cited: Iterable[dict[str, Any]]) -> bool:
    kinds = {str(row.get("kind", "")) for row in cited}
    if required == "transcript":
        return "transcript" in kinds
    if required == "visual":
        return bool(kinds & {"frame", "clip"})
    if required == "clip":
        return "clip" in kinds
    if required == "mixed":
        return "transcript" in kinds and bool(kinds & {"frame", "clip"})
    raise ValueError(f"unknown required modality: {required}")


def _window_matches(window: object, cited: Iterable[dict[str, Any]]) -> bool:
    if window is None:
        return True
    if not isinstance(window, list) or len(window) != 2:
        raise ValueError("expected_evidence_window must be [start_s, end_s]")
    expected_start, expected_end = float(window[0]), float(window[1])
    for row in cited:
        start = float(row.get("start_s", -1))
        end = float(row.get("end_s", start))
        if end >= expected_start and start <= expected_end:
            return True
    return False


def evaluate_prediction(prediction: dict[str, Any], gold: dict[str, Any]) -> EvaluationResult:
    case_id = str(gold["case_id"])
    if str(prediction.get("case_id", "")) != case_id:
        raise ValueError("prediction/gold case_id mismatch")
    accepted = {str(gold["reference_answer"]), *(str(item) for item in gold.get("accepted_aliases", []))}
    try:
        short_answer = parse_final_answer(str(prediction.get("answer", "")))
    except FinalAnswerFormatError:
        short_answer = ""
    answer_correct = _normalize_answer(short_answer) in {_normalize_answer(item) for item in accepted}
    cited = _cited_evidence(prediction)
    citation_valid = bool(cited)
    modality_correct = citation_valid and _modality_matches(str(gold["required_modality"]), cited)
    evidence_window_correct = citation_valid and _window_matches(gold.get("expected_evidence_window"), cited)
    passed = answer_correct and citation_valid and modality_correct and evidence_window_correct
    return EvaluationResult(
        case_id=case_id,
        answer_correct=answer_correct,
        citation_valid=citation_valid,
        modality_correct=modality_correct,
        evidence_window_correct=evidence_window_correct,
        passed=passed,
    )


def evaluate_predictions(predictions: Iterable[dict[str, Any]], gold_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    gold_by_id = {str(row["case_id"]): row for row in gold_rows}
    prediction_rows = {str(row["case_id"]): row for row in predictions}
    if set(prediction_rows) != set(gold_by_id):
        raise ValueError("prediction IDs do not exactly match gold IDs")
    results = [evaluate_prediction(prediction_rows[case_id], gold_by_id[case_id]) for case_id in gold_by_id]
    n = len(results)
    transcript = [result for result in results if gold_by_id[result.case_id]["required_modality"] == "transcript"]
    visual = [result for result in results if gold_by_id[result.case_id]["required_modality"] != "transcript"]
    visual_tools = {"inspect_frame", "inspect_clip"}
    def used_visual(case_id: str) -> bool:
        return bool(set(prediction_rows[case_id].get("tool_calls", [])) & visual_tools)
    def rate(values: list[bool]) -> float:
        return sum(values) / len(values) if values else 0.0
    latencies = [float(row["latency_ms"]) for row in prediction_rows.values() if row.get("latency_ms") is not None]
    latencies.sort()
    percentile = lambda p: latencies[min(len(latencies) - 1, max(0, int(p * len(latencies) + 0.9999999999) - 1))] if latencies else None
    usage = {}
    for field in ("api_calls", "input_tokens", "output_tokens", "total_tokens", "estimated_cost_usd"):
        values = [row.get("usage", {}).get(field) for row in prediction_rows.values()]
        numeric = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
        usage[field] = sum(numeric) if numeric else None
    return {
        "cases": n,
        "answer_correct": {"overall": rate([r.answer_correct for r in results]), "transcript_only": rate([r.answer_correct for r in transcript]), "visual_required": rate([r.answer_correct for r in visual])},
        "full_pass": {"overall": rate([r.passed for r in results]), "transcript_only": rate([r.passed for r in transcript]), "visual_required": rate([r.passed for r in visual])},
        "visual_tool_use_on_visual_required": rate([used_visual(r.case_id) for r in visual]),
        "unnecessary_visual_use_on_transcript": rate([used_visual(r.case_id) for r in transcript]),
        "total_tool_calls": sum(len(row.get("tool_calls", [])) for row in prediction_rows.values()),
        "average_tool_calls": sum(len(row.get("tool_calls", [])) for row in prediction_rows.values()) / n,
        "mean_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "p50_latency_ms": percentile(0.50), "p95_latency_ms": percentile(0.95),
        "failure_or_abstention_count": sum(row.get("status") != "answered" for row in prediction_rows.values()),
        "usage": usage,
        "per_case": [dict(result.to_dict(), answer=prediction_rows[result.case_id].get("answer", ""), status=prediction_rows[result.case_id].get("status"), evidence=prediction_rows[result.case_id].get("evidence", []), activity=prediction_rows[result.case_id].get("activity", []), latency_ms=prediction_rows[result.case_id].get("latency_ms"), tool_calls=prediction_rows[result.case_id].get("tool_calls", []), usage=prediction_rows[result.case_id].get("usage", {})) for result in results],
    }
