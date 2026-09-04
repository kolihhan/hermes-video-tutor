from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from .activity import ActivityStore
from .contracts import ActivityEvent, Evidence
from .course import load_course_manifest
from .evidence import EvidenceStore
from .media import FfmpegMediaInspector, MediaError
from .transcript import TranscriptIndex, load_transcript


class ToolRuntimeError(RuntimeError):
    pass


class VideoToolRuntime:
    def __init__(
        self,
        *,
        course_manifest: str | Path,
        session_dir: str | Path,
        max_clip_s: float = 15.0,
        max_frames: int = 4,
        max_image_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        self.course = load_course_manifest(course_manifest)
        self.session_dir = Path(session_dir).resolve()
        self.evidence = EvidenceStore(self.session_dir)
        self.activity = ActivityStore(self.session_dir)
        self.transcript = TranscriptIndex(load_transcript(self.course.transcript_path))
        self.media = FfmpegMediaInspector(
            media_root=self.course.video_path.parent,
            cache_dir=self.session_dir / "media-cache",
            max_clip_s=max_clip_s,
            max_frames=max_frames,
        )
        self.max_image_bytes = max_image_bytes

    def execute(self, name: str, arguments: dict[str, Any]) -> str | dict[str, Any]:
        if not isinstance(arguments, dict):
            return self._error(name, "tool arguments must be an object")
        try:
            if name == "search_transcript":
                return self._search(arguments)
            if name == "expand_context":
                return self._expand(arguments)
            if name == "inspect_frame":
                return self._frame(arguments)
            if name == "inspect_clip":
                return self._clip(arguments)
            return self._error(name, f"unknown video tutor tool: {name}")
        except (ValueError, KeyError, MediaError, ToolRuntimeError) as exc:
            return self._error(name, str(exc))

    def _search(self, args: dict[str, Any]) -> str:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ToolRuntimeError("query is required")
        top_k = int(args.get("top_k", 5))
        if not 1 <= top_k <= 10:
            raise ToolRuntimeError("top_k must be between 1 and 10")
        hits = self.transcript.search(query, top_k=top_k)
        records: list[Evidence] = []
        for hit in hits:
            s = hit.segment
            records.append(self.evidence.add(
                kind="transcript", start_s=s.start_s, end_s=s.end_s, text=s.text
            ))
        self._activity("search_transcript", f"Found {len(records)} transcript segment(s).", records)
        return self._text_result("Transcript search results", records)

    def _expand(self, args: dict[str, Any]) -> str:
        segment_id = str(args.get("segment_id", "")).strip()
        if not segment_id:
            raise ToolRuntimeError("segment_id is required")
        before = float(args.get("before_s", 30.0))
        after = float(args.get("after_s", 30.0))
        segments = self.transcript.expand_context(segment_id, before_s=before, after_s=after)
        text = "\n".join(f"[{s.start_s:.1f}-{s.end_s:.1f}] {s.text}" for s in segments)
        record = self.evidence.add(
            kind="transcript",
            start_s=min(s.start_s for s in segments),
            end_s=max(s.end_s for s in segments),
            text=text,
        )
        self._activity("expand_context", f"Expanded transcript around {segment_id}.", [record])
        return self._text_result("Expanded transcript context", [record])

    def _frame(self, args: dict[str, Any]) -> dict[str, Any]:
        timestamp = float(args["timestamp_s"])
        inspection = self.media.inspect_frame(self.course.video_path.name, timestamp)
        record = self.evidence.add(
            kind="frame", start_s=timestamp, end_s=timestamp,
            text=f"Visual frame from {self.course.title} at {timestamp:.1f}s.",
            media_paths=inspection.image_paths,
        )
        self._activity("inspect_frame", f"Inspected frame at {timestamp:.1f}s.", [record])
        return self._multimodal_result("Visual frame evidence", [record])

    def _clip(self, args: dict[str, Any]) -> dict[str, Any]:
        start = float(args["start_s"])
        end = float(args["end_s"])
        frame_count = int(args.get("frame_count", 3))
        inspection = self.media.inspect_clip(
            self.course.video_path.name, start, end, frame_count=frame_count
        )
        overlapping = [s for s in self.transcript.segments if s.end_s >= start and s.start_s <= end]
        transcript_text = " ".join(s.text for s in overlapping).strip()
        text = f"Sampled {frame_count} frame(s) from {start:.1f}-{end:.1f}s."
        if transcript_text:
            text += f" Overlapping transcript: {transcript_text}"
        record = self.evidence.add(
            kind="clip", start_s=start, end_s=end, text=text,
            media_paths=inspection.image_paths,
        )
        self._activity("inspect_clip", f"Inspected clip {start:.1f}-{end:.1f}s using {frame_count} sampled frames.", [record])
        return self._multimodal_result("Clip evidence", [record])

    def _text_result(self, summary: str, records: list[Evidence]) -> str:
        return json.dumps({
            "summary": summary,
            "evidence": [self._evidence_payload(item) for item in records],
        }, ensure_ascii=False)

    def _multimodal_result(self, summary: str, records: list[Evidence]) -> dict[str, Any]:
        text = self._text_result(summary, records)
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        for record in records:
            for raw_path in record.media_paths:
                path = Path(raw_path).resolve()
                data = path.read_bytes()
                if len(data) > self.max_image_bytes:
                    raise ToolRuntimeError(f"visual evidence exceeds {self.max_image_bytes} byte limit")
                encoded = base64.b64encode(data).decode("ascii")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                })
        return {
            "_multimodal": True,
            "content": content,
            "text_summary": summary + " Evidence: " + " ".join(f"[{r.evidence_id}]" for r in records),
            "meta": {"tool_domain": "video_tutor", "evidence_ids": [r.evidence_id for r in records]},
        }

    @staticmethod
    def _evidence_payload(record: Evidence) -> dict[str, Any]:
        return {
            "id": record.evidence_id,
            "kind": record.kind,
            "start_s": record.start_s,
            "end_s": record.end_s,
            "text": record.text,
        }

    def _activity(self, tool: str, summary: str, records: list[Evidence]) -> None:
        self.activity.add(ActivityEvent(
            tool=tool,
            summary=summary,
            evidence_ids=tuple(item.evidence_id for item in records),
        ))

    @staticmethod
    def _error(tool: str, error: str) -> str:
        return json.dumps({"error": error, "tool": tool}, ensure_ascii=False)
