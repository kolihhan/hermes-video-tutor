from __future__ import annotations

import os


def _handler(name):
    def handle(args, **kwargs):
        from video_tutor.plugin_bridge import execute_tool
        return execute_tool(name, args)
    return handle


def _schema(description, properties, required):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
        "description": description,
    }


def register(ctx):
    ctx.register_tool(
        name="search_transcript",
        toolset="video_tutor",
        schema=_schema(
            "Search the lecture transcript for relevant timestamped evidence.",
            {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            ["query"],
        ),
        handler=_handler("search_transcript"),
    )
    ctx.register_tool(
        name="expand_context",
        toolset="video_tutor",
        schema=_schema(
            "Expand transcript context around a known transcript segment.",
            {
                "segment_id": {"type": "string"},
                "before_s": {"type": "number", "minimum": 0, "default": 30},
                "after_s": {"type": "number", "minimum": 0, "default": 30},
            },
            ["segment_id"],
        ),
        handler=_handler("expand_context"),
    )
    mode = os.environ.get("VIDEO_TUTOR_TOOL_MODE", "multimodal").strip().lower()
    if mode not in {"transcript_only", "multimodal"}:
        raise ValueError("VIDEO_TUTOR_TOOL_MODE must be transcript_only or multimodal")
    if mode == "transcript_only":
        return
    ctx.register_tool(
        name="inspect_frame",
        toolset="video_tutor",
        schema=_schema(
            "Inspect the actual video frame at a timestamp when transcript text is insufficient.",
            {"timestamp_s": {"type": "number", "minimum": 0}},
            ["timestamp_s"],
        ),
        handler=_handler("inspect_frame"),
    )
    ctx.register_tool(
        name="inspect_clip",
        toolset="video_tutor",
        schema=_schema(
            "Inspect a short video interval as sampled visual frames plus overlapping transcript context.",
            {
                "start_s": {"type": "number", "minimum": 0},
                "end_s": {"type": "number", "minimum": 0},
                "frame_count": {"type": "integer", "minimum": 1, "maximum": 4, "default": 3},
            },
            ["start_s", "end_s"],
        ),
        handler=_handler("inspect_clip"),
    )
