from pathlib import Path
import re

ROOT = Path(__file__).parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_windows_setup_is_project_local_pinned_and_checks_dependencies():
    text = _read("scripts/setup-hermes.ps1")
    lowered = text.lower()
    assert ".run" in text
    assert "HERMES_HOME" in text
    assert "8911e2e0ed" in text
    assert "NousResearch/hermes-agent" in text
    assert "ffmpeg" in lowered
    assert "ollama" in lowered
    assert "uv" in lowered
    assert "Set-ExecutionPolicy" not in text
    assert not re.search(r"\$(?:pid)\b", text, re.IGNORECASE)


def test_windows_launcher_uses_process_scoped_bypass_and_project_temp():
    cmd = _read("run-demo.cmd")
    ps1 = _read("scripts/run-demo.ps1")
    assert "-ExecutionPolicy Bypass" in cmd
    assert ".run" in ps1
    assert "$env:TEMP" in ps1 and "$env:TMP" in ps1
    assert "Set-ExecutionPolicy" not in ps1
    assert not re.search(r"\$(?:pid)\b", ps1, re.IGNORECASE)


def test_project_config_keeps_tool_search_eager_and_does_not_mutate_global_home():
    config = _read("config/hermes-project.yaml")
    assert 'enabled: "off"' in config
    setup = _read("scripts/setup-hermes.ps1")
    assert "Copy-Item" in setup
    assert "config/hermes-project.yaml" in setup.replace("\\", "/")
