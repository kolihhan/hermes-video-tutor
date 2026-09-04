from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .evaluate import evaluate_prediction

ROOT = Path(__file__).resolve().parent


def _load_json(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected a JSON list of objects: {path.name}")
    return rows


def load_fixture_predictions(mode: str) -> list[dict[str, Any]]:
    if mode not in {"transcript_only", "multimodal"}:
        raise ValueError("mode must be transcript_only or multimodal")
    return _load_json(ROOT / "fixtures" / f"{mode}_predictions.json")


def evaluate_fixture(mode: str) -> dict[str, Any]:
    predictions = load_fixture_predictions(mode)
    gold_rows = _load_json(ROOT / "gold_labels.json")
    gold_by_id = {str(row["case_id"]): row for row in gold_rows}
    if set(gold_by_id) != {str(row.get("case_id")) for row in predictions}:
        raise ValueError("fixture prediction IDs do not match gold label IDs")

    results = [evaluate_prediction(row, gold_by_id[str(row["case_id"])]) for row in predictions]
    n = len(results)
    visual_ids = {
        str(row["case_id"])
        for row in gold_rows
        if str(row["required_modality"]) in {"visual", "clip", "mixed"}
    }
    transcript_ids = {
        str(row["case_id"])
        for row in gold_rows
        if str(row["required_modality"]) == "transcript"
    }

    prediction_by_id = {str(row["case_id"]): row for row in predictions}
    visual_tools = {"inspect_frame", "inspect_clip"}

    def used_visual(case_id: str) -> bool:
        return bool(set(prediction_by_id[case_id].get("tool_calls", [])) & visual_tools)

    return {
        "mode": mode,
        "cases": n,
        "answer_accuracy": sum(result.answer_correct for result in results) / n,
        "valid_citation_rate": sum(result.citation_valid for result in results) / n,
        "full_pass_rate": sum(result.passed for result in results) / n,
        "visual_tool_usage_when_required": (
            sum(used_visual(case_id) for case_id in visual_ids) / len(visual_ids) if visual_ids else 0.0
        ),
        "unnecessary_visual_usage_on_transcript": (
            sum(used_visual(case_id) for case_id in transcript_ids) / len(transcript_ids) if transcript_ids else 0.0
        ),
        "avg_tool_calls": sum(len(row.get("tool_calls", [])) for row in predictions) / n,
        "per_case": [result.to_dict() for result in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate frozen product-sanity prediction fixtures")
    parser.add_argument("--mode", choices=["transcript_only", "multimodal", "both"], default="both")
    args = parser.parse_args()
    modes = ["transcript_only", "multimodal"] if args.mode == "both" else [args.mode]
    payload = {mode: evaluate_fixture(mode) for mode in modes}
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
