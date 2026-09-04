import hashlib
import json
from pathlib import Path
import subprocess

from video_tutor.course import load_course_manifest
from video_tutor.transcript import load_transcript


def test_demo_fixture_is_neutral_and_contains_no_visual_answer_in_transcript():
    root = Path(__file__).parents[1]
    course = load_course_manifest(root / "demo" / "course.json")
    segments = load_transcript(course.transcript_path)
    text = " ".join(s.text.lower() for s in segments)
    assert course.title == "Evidence-Aware Tutor Demo"
    assert "blue" not in text
    assert "green" not in text
    assert course.video_path.is_file() and course.video_path.stat().st_size > 0
    questions = json.loads((root / "demo" / "questions.json").read_text(encoding="utf-8"))
    assert {q["type"] for q in questions} == {"transcript", "visual", "temporal"}


def test_live_fixture_transcript_names_visual_windows_without_visual_answers():
    root = Path(__file__).parents[1]
    segments = load_transcript(root / "evaluation" / "fixture" / "transcript.json")
    assert len(segments) == 12
    visual_text = " ".join(segment.text.lower() for segment in segments[6:])
    assert all(f"checkpoint {letter.lower()}" in visual_text for letter in "ABCDEF")
    assert {"blue", "seven", "square", "right", "go", "green"}.isdisjoint(visual_text.split())


def test_live_fixture_has_green_full_screen_background_at_57_seconds():
    root = Path(__file__).parents[1]
    video = root / "evaluation" / "fixture" / "media" / "lecture.mp4"
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", "57",
            "-i", str(video), "-vf", "crop=1:1:0:0,format=rgb24",
            "-frames:v", "1", "-f", "rawvideo", "-",
        ],
        capture_output=True,
        check=True,
    )
    red, green, blue = result.stdout[:3]
    assert green > 80 and green > red * 2 and green > blue * 2


def test_live_fixture_provenance_hashes_every_generated_asset_and_generator():
    root = Path(__file__).parents[1]
    fixture = root / "evaluation" / "fixture"
    provenance = json.loads((fixture / "provenance.json").read_text(encoding="utf-8"))
    expected = {
        "course.json": fixture / "course.json",
        "transcript.json": fixture / "transcript.json",
        "media/lecture.mp4": fixture / "media" / "lecture.mp4",
    }
    generator = root / Path(str(provenance["generator"]).replace("\\", "/"))
    assert provenance["generator_sha256"] == hashlib.sha256(generator.read_bytes()).hexdigest()
    assert provenance["asset_sha256"] == {
        name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in expected.items()
    }
