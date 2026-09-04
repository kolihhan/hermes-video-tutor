from pathlib import Path
import subprocess

import pytest

from video_tutor.media import FfmpegMediaInspector, MediaError


def _make_video(path: Path) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x180:d=3:r=5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
    ], check=True)


def test_inspect_frame_extracts_bounded_image(tmp_path):
    media = tmp_path / "media"
    cache = tmp_path / "cache"
    media.mkdir()
    video = media / "lecture.mp4"
    _make_video(video)
    inspector = FfmpegMediaInspector(media_root=media, cache_dir=cache)
    result = inspector.inspect_frame("lecture.mp4", 1.0)
    assert len(result.image_paths) == 1
    frame = Path(result.image_paths[0])
    assert frame.is_file() and frame.stat().st_size > 0
    assert frame.resolve().is_relative_to(cache.resolve())


def test_inspect_clip_samples_frames_and_enforces_duration(tmp_path):
    media = tmp_path / "media"
    cache = tmp_path / "cache"
    media.mkdir()
    _make_video(media / "lecture.mp4")
    inspector = FfmpegMediaInspector(media_root=media, cache_dir=cache, max_clip_s=2.0, max_frames=3)
    result = inspector.inspect_clip("lecture.mp4", 0.0, 2.0, frame_count=3)
    assert len(result.image_paths) == 3
    with pytest.raises(MediaError, match="duration"):
        inspector.inspect_clip("lecture.mp4", 0.0, 2.5, frame_count=3)
    with pytest.raises(MediaError, match="frame_count"):
        inspector.inspect_clip("lecture.mp4", 0.0, 1.0, frame_count=4)


def test_media_path_cannot_escape_course_root(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    outside = tmp_path / "secret.mp4"
    outside.write_bytes(b"secret")
    inspector = FfmpegMediaInspector(media_root=media, cache_dir=tmp_path / "cache")
    with pytest.raises(MediaError, match="outside media root"):
        inspector.inspect_frame("../secret.mp4", 0)
