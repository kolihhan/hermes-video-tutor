"""Generate the self-authored 60-second P3 fixture with ffmpeg only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).parents[1]
OUT = ROOT / "evaluation" / "fixture"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate() -> None:
    media = OUT / "media"
    media.mkdir(parents=True, exist_ok=True)
    video = media / "lecture.mp4"
    font = Path("C:/Windows/Fonts/arial.ttf")
    if not font.is_file():
        raise FileNotFoundError(f"fixture font not found: {font}")
    draw = (
        "drawbox=x=80:y=90:w=480:h=180:color=blue@1:t=fill:enable='between(t,30,35)',"
        "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='7':x=310:y=150:fontsize=72:fontcolor=white:enable='between(t,35,40)',"
        "drawbox=x=80:y=90:w=180:h=180:color=white@1:t=fill:enable='between(t,40,45)',"
        "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='SQUARE':x=95:y=150:fontsize=28:fontcolor=black:enable='between(t,40,45)',"
        "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='>':x=300:y=150:fontsize=72:fontcolor=white:enable='between(t,45,50)',"
        "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='GO':x=280:y=150:fontsize=64:fontcolor=white:enable='between(t,50,55)',"
        "drawbox=x=0:y=0:w=iw:h=ih:color=green@1:t=fill:enable='between(t,55,60)'"
    )
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
        "-i", "color=c=black:s=640x360:d=60:r=2", "-vf", draw,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video),
    ], check=True)
    (OUT / "transcript.json").write_text(json.dumps([
        {"segment_id": "t01", "start_s": 0, "end_s": 5, "text": "The project codename is Orion."},
        {"segment_id": "t02", "start_s": 5, "end_s": 10, "text": "The three workflow stages are collect, compare, decide."},
        {"segment_id": "t03", "start_s": 10, "end_s": 15, "text": "The checkpoint interval is five minutes."},
        {"segment_id": "t04", "start_s": 15, "end_s": 20, "text": "The owning team is Atlas."},
        {"segment_id": "t05", "start_s": 20, "end_s": 25, "text": "The retry limit is two attempts."},
        {"segment_id": "t06", "start_s": 25, "end_s": 30, "text": "The final readiness signal is ready."},
        {"segment_id": "v01", "start_s": 30, "end_s": 35, "text": "Checkpoint A is visible now."},
        {"segment_id": "v02", "start_s": 35, "end_s": 40, "text": "Checkpoint B is visible now."},
        {"segment_id": "v03", "start_s": 40, "end_s": 45, "text": "Checkpoint C is visible now."},
        {"segment_id": "v04", "start_s": 45, "end_s": 50, "text": "Checkpoint D is visible now."},
        {"segment_id": "v05", "start_s": 50, "end_s": 55, "text": "Checkpoint E is visible now."},
        {"segment_id": "v06", "start_s": 55, "end_s": 60, "text": "Checkpoint F is visible now."},
    ], indent=2) + "\n", encoding="utf-8", newline="\n")
    course = OUT / "course.json"
    transcript = OUT / "transcript.json"
    course.write_text(json.dumps({"course_id": "p3-fixture", "title": "Self-authored P3 fixture", "video_path": "media/lecture.mp4", "transcript_path": "transcript.json"}, indent=2) + "\n", encoding="utf-8", newline="\n")
    ffmpeg_version = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    generator = Path(__file__)
    (OUT / "provenance.json").write_text(json.dumps({
        "license": "CC0-1.0", "source": "self-authored geometric/text instructions; no external media",
        "generator": generator.relative_to(ROOT).as_posix(), "generator_sha256": _sha256(generator),
        "ffmpeg_version": ffmpeg_version,
        "font": str(font), "font_sha256": _sha256(font),
        "asset_sha256": {
            "course.json": _sha256(course),
            "transcript.json": _sha256(transcript),
            "media/lecture.mp4": _sha256(video),
        },
        "duration_s": 60,
    }, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate()
