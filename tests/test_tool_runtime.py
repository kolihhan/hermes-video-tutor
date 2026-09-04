import json
from pathlib import Path
import subprocess

import pytest

from video_tutor.course import load_course_manifest
from video_tutor.tool_runtime import VideoToolRuntime


def _fixture(root: Path) -> Path:
    media = root / "media"
    media.mkdir()
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=3:r=5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(media / "lecture.mp4"),
    ], check=True)
    transcript = root / "transcript.json"
    transcript.write_text(json.dumps([
        {"segment_id":"s1","start_s":0,"end_s":1.5,"text":"The lecturer introduces the pipeline."},
        {"segment_id":"s2","start_s":1.5,"end_s":3,"text":"The highlighted component is visible on the slide."},
    ]), encoding="utf-8")
    manifest = root / "course.json"
    manifest.write_text(json.dumps({
        "course_id":"demo",
        "title":"Demo Lecture",
        "video_path":"media/lecture.mp4",
        "transcript_path":"transcript.json"
    }), encoding="utf-8")
    return manifest


def test_course_manifest_rejects_annotation_like_metadata(tmp_path):
    manifest = tmp_path / "course.json"
    manifest.write_text(json.dumps({
        "course_id":"x", "title":"x", "video_path":"x.mp4", "transcript_path":"x.json",
        "caption":"the answer is blue"
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected course metadata"):
        load_course_manifest(manifest)


def test_transcript_tool_commits_evidence_and_activity(tmp_path):
    manifest = _fixture(tmp_path)
    runtime = VideoToolRuntime(course_manifest=manifest, session_dir=tmp_path / "session")
    result = runtime.execute("search_transcript", {"query":"pipeline", "top_k":1})
    payload = json.loads(result)
    assert payload["evidence"][0]["id"] == "E1"
    assert payload["evidence"][0]["kind"] == "transcript"
    assert runtime.evidence.all()[0].text.startswith("The lecturer")
    assert runtime.activity.all()[0].tool == "search_transcript"


def test_frame_tool_returns_current_hermes_multimodal_envelope(tmp_path):
    manifest = _fixture(tmp_path)
    runtime = VideoToolRuntime(course_manifest=manifest, session_dir=tmp_path / "session")
    result = runtime.execute("inspect_frame", {"timestamp_s":2.0})
    assert isinstance(result, dict)
    assert result["_multimodal"] is True
    assert result["content"][0]["type"] == "text"
    image = result["content"][1]
    assert image["type"] == "image_url"
    assert image["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert result["meta"]["evidence_ids"] == ["E1"]
