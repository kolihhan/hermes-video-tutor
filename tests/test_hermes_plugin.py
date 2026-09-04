import importlib.util
from pathlib import Path
import yaml


def test_project_plugin_manifest_and_registration_surface():
    root = Path(__file__).parents[1]
    plugin_dir = root / ".hermes" / "plugins" / "video_tutor"
    manifest = yaml.safe_load((plugin_dir / "plugin.yaml").read_text(encoding="utf-8"))
    assert manifest["name"] == "video_tutor"
    assert set(manifest["provides_tools"]) == {
        "search_transcript", "expand_context", "inspect_frame", "inspect_clip"
    }

    spec = importlib.util.spec_from_file_location("video_tutor_project_plugin", plugin_dir / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class Ctx:
        def __init__(self): self.calls = []
        def register_tool(self, **kwargs): self.calls.append(kwargs)

    ctx = Ctx()
    module.register(ctx)
    assert {call["name"] for call in ctx.calls} == set(manifest["provides_tools"])
    assert all(call["toolset"] == "video_tutor" for call in ctx.calls)
    assert all(call["schema"]["additionalProperties"] is False for call in ctx.calls)


def test_project_hermes_config_disables_tool_search_and_enables_only_plugin():
    root = Path(__file__).parents[1]
    config = yaml.safe_load((root / "config" / "hermes-project.yaml").read_text(encoding="utf-8"))
    assert config["tools"]["tool_search"]["enabled"] == "off"
    assert config["plugins"]["enabled"] == ["video_tutor"]
    assert (root / "Modelfile.hermes").read_text(encoding="utf-8").splitlines()[-1] == "PARAMETER temperature 0"


def test_plugin_can_register_transcript_only_baseline(monkeypatch):
    root = Path(__file__).parents[1]
    plugin_dir = root / ".hermes" / "plugins" / "video_tutor"
    spec = importlib.util.spec_from_file_location("video_tutor_project_plugin_baseline", plugin_dir / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    monkeypatch.setenv("VIDEO_TUTOR_TOOL_MODE", "transcript_only")
    class Ctx:
        def __init__(self): self.calls=[]
        def register_tool(self, **kwargs): self.calls.append(kwargs)
    ctx=Ctx(); module.register(ctx)
    assert {c["name"] for c in ctx.calls} == {"search_transcript", "expand_context"}
