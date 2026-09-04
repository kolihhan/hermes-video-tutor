from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .bootstrap import build_tutor_service
from .tutor import TutorService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-tutor", description="Hermes-powered evidence-aware video tutor")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Ask the first question from the bundled demo")
    demo.add_argument("--course", default=None)

    ask = sub.add_parser("ask", help="Ask a question about a course")
    ask.add_argument("question")
    ask.add_argument("--course", default=None)

    inspect = sub.add_parser("inspect", help="Ask and print observable tool activity/evidence")
    inspect.add_argument("--question", required=True)
    inspect.add_argument("--course", default=None)
    return parser


def run_cli(argv: Sequence[str] | None = None, *, service: TutorService | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    course = Path(args.course).resolve() if args.course else (root / "demo" / "course.json").resolve()
    tutor = service or build_tutor_service(repo_root=root)

    if args.command == "demo":
        rows = json.loads((root / "demo" / "questions.json").read_text(encoding="utf-8"))
        question = str(rows[0]["question"])
    elif args.command == "ask":
        question = args.question
    else:
        question = args.question

    answer = tutor.ask(question=question, course_manifest=course)
    print(answer.text)
    if args.command == "inspect":
        print("\nAgent Activity")
        for event in answer.activity:
            suffix = " " + ", ".join(event.evidence_ids) if event.evidence_ids else ""
            print(f"- {event.tool}: {event.summary}{suffix}")
        print("\nEvidence")
        for item in answer.evidence:
            print(f"- {item.evidence_id} [{item.kind}] {item.start_s:.1f}-{item.end_s:.1f}s: {item.text}")
    return 0


def main() -> None:
    raise SystemExit(run_cli())

if __name__ == "__main__":
    main()
