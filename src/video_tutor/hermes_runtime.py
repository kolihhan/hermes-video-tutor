from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import Protocol


@dataclass(frozen=True)
class RuntimeRequest:
    question: str
    course_manifest: Path
    session_dir: Path


class AgentRuntime(Protocol):
    def ask(self, request: RuntimeRequest) -> str: ...


class HermesRuntimeError(RuntimeError):
    pass


class HermesCliRuntime:
    """Narrow integration boundary around Hermes' scripted one-shot CLI.

    Hermes owns the observe/act loop and tool dispatch. This adapter only
    supplies a project-scoped environment and captures the final answer.
    Tool activity/evidence is persisted by the project plugin itself.
    """

    def __init__(
        self,
        *,
        repo_root: str | Path,
        hermes_home: str | Path,
        executable: str = "hermes",
        timeout_s: float = 300.0,
        tool_mode: str = "multimodal",
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.hermes_home = Path(hermes_home).resolve()
        self.executable = executable
        self.timeout_s = timeout_s
        if tool_mode not in {"transcript_only", "multimodal"}:
            raise ValueError("tool_mode must be transcript_only or multimodal")
        self.tool_mode = tool_mode

    def ask(self, request: RuntimeRequest) -> str:
        question = request.question.strip()
        if not question:
            raise HermesRuntimeError("question must not be empty")
        request.session_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "HERMES_HOME": str(self.hermes_home),
            "HERMES_ENABLE_PROJECT_PLUGINS": "1",
            "VIDEO_TUTOR_COURSE": str(request.course_manifest.resolve()),
            "VIDEO_TUTOR_SESSION": str(request.session_dir.resolve()),
            "VIDEO_TUTOR_TOOL_MODE": self.tool_mode,
        })
        src = str((self.repo_root / "src").resolve())
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = src + (os.pathsep + current_pythonpath if current_pythonpath else "")
        prompt = self._prompt(question)
        command = [
            self.executable, "-z", prompt,
            "--toolsets", "video_tutor",
            "--usage-file", str(request.session_dir / "hermes-usage.json"),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.repo_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except FileNotFoundError as exc:
            raise HermesRuntimeError("Hermes CLI was not found. Run scripts/setup-hermes.ps1 first.") from exc
        except subprocess.TimeoutExpired as exc:
            raise HermesRuntimeError(f"Hermes run exceeded {self.timeout_s:g}s") from exc
        answer = completed.stdout.strip()
        if completed.returncode != 0:
            detail = completed.stderr.strip() or f"exit code {completed.returncode}"
            raise HermesRuntimeError(f"Hermes failed: {detail}")
        if not answer:
            raise HermesRuntimeError("Hermes returned an empty final answer")
        return answer

    @staticmethod
    def _prompt(question: str) -> str:
        return (
            "You are a tutor answering questions about the configured lecture. "
            "Use the video_tutor evidence tools autonomously when needed. "
            "Choose only the tools needed for the question; do not follow a fixed tool sequence. "
            "Every factual answer about the lecture must cite evidence IDs such as [E1]. "
            "For visual claims, inspect actual frame or clip evidence rather than guessing from transcript text. "
            "When evidence is sufficient, return exactly: FINAL: <short answer> [E#]. "
            "Use a short canonical answer phrase, followed only by one or more evidence citations; do not add explanatory prose. "
            "If the available evidence cannot establish the answer within your action budget, reply exactly "
            "INSUFFICIENT_EVIDENCE. Do not expose hidden chain-of-thought; only return the required final format.\n\n"
            f"Student question: {question}"
        )
