from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import shutil
import subprocess


class MediaError(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaInspection:
    image_paths: tuple[str, ...]


class FfmpegMediaInspector:
    def __init__(
        self,
        *,
        media_root: str | Path,
        cache_dir: str | Path,
        max_clip_s: float = 15.0,
        max_frames: int = 4,
        ffmpeg: str = "ffmpeg",
    ) -> None:
        if max_clip_s <= 0 or max_frames <= 0:
            raise ValueError("media budgets must be positive")
        self.media_root = Path(media_root).resolve()
        self.cache_dir = Path(cache_dir).resolve()
        self.max_clip_s = float(max_clip_s)
        self.max_frames = int(max_frames)
        self.ffmpeg = ffmpeg

    def inspect_frame(self, video: str, timestamp_s: float) -> MediaInspection:
        timestamp = self._finite_nonnegative(timestamp_s, "timestamp")
        video_path = self._resolve_video(video)
        output = self.cache_dir / f"frame-{self._key(video_path, timestamp):s}.jpg"
        self._extract(video_path, timestamp, output)
        return MediaInspection((str(output),))

    def inspect_clip(
        self,
        video: str,
        start_s: float,
        end_s: float,
        *,
        frame_count: int = 3,
    ) -> MediaInspection:
        start = self._finite_nonnegative(start_s, "start")
        end = self._finite_nonnegative(end_s, "end")
        if end <= start:
            raise MediaError("clip end must be greater than start")
        if end - start > self.max_clip_s + 1e-9:
            raise MediaError(f"clip duration exceeds {self.max_clip_s:g}s limit")
        if isinstance(frame_count, bool) or not isinstance(frame_count, int) or not 1 <= frame_count <= self.max_frames:
            raise MediaError(f"frame_count must be between 1 and {self.max_frames}")
        video_path = self._resolve_video(video)
        if frame_count == 1:
            times = [start + (end - start) / 2]
        else:
            step = (end - start) / (frame_count - 1)
            times = [start + i * step for i in range(frame_count)]
        paths: list[str] = []
        for index, timestamp in enumerate(times):
            output = self.cache_dir / f"clip-{self._key(video_path, start, end, frame_count)}-{index}.jpg"
            self._extract(video_path, timestamp, output)
            paths.append(str(output))
        return MediaInspection(tuple(paths))

    def _resolve_video(self, raw: str) -> Path:
        candidate = (self.media_root / raw).resolve()
        try:
            candidate.relative_to(self.media_root)
        except ValueError as exc:
            raise MediaError("video path is outside media root") from exc
        if not candidate.is_file():
            raise MediaError(f"video does not exist: {raw}")
        return candidate

    def _extract(self, video: Path, timestamp: float, output: Path) -> None:
        if output.is_file() and output.stat().st_size > 0:
            return
        if shutil.which(self.ffmpeg) is None:
            raise MediaError(f"ffmpeg executable not found: {self.ffmpeg}")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(".tmp.jpg")
        command = [
            self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{timestamp:.3f}", "-i", str(video),
            "-frames:v", "1", "-q:v", "3", str(tmp),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            tmp.unlink(missing_ok=True)
            raise MediaError(f"ffmpeg frame extraction failed: {exc}") from exc
        if completed.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
            tmp.unlink(missing_ok=True)
            detail = completed.stderr.strip() or "empty frame output"
            raise MediaError(f"ffmpeg frame extraction failed: {detail}")
        tmp.replace(output)

    @staticmethod
    def _finite_nonnegative(value: float, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MediaError(f"{name} must be a number")
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise MediaError(f"{name} must be finite and non-negative")
        return number

    @staticmethod
    def _key(video: Path, *parts: object) -> str:
        payload = "|".join([str(video), str(video.stat().st_mtime_ns), *(str(p) for p in parts)])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
