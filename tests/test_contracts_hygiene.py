from dataclasses import fields
from pathlib import Path


def test_runtime_contracts_do_not_expose_evaluation_labels():
    from video_tutor.contracts import Course, TutorAnswer

    forbidden = {"gold", "reference_answer", "annotation", "caption", "required_modality", "expected_evidence"}
    names = {f.name for typ in (Course, TutorAnswer) for f in fields(typ)}
    assert forbidden.isdisjoint(names)


def test_runtime_source_does_not_import_evaluation_or_embed_gold_terms():
    root = Path(__file__).parents[1] / "src" / "video_tutor"
    forbidden_imports = ("import evaluation", "from evaluation")
    forbidden_runtime_tokens = ("reference_answer", "required_modality", "expected_evidence_window", "annotation.caption")
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert not any(token in lowered for token in forbidden_imports), path
        assert not any(token in lowered for token in forbidden_runtime_tokens), path
