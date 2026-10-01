from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_readme_has_30_second_product_story_and_honest_evaluation_language():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "video tutor" in lower and "hermes" in lower
    headings = (
        "## Demo",
        "## Key result",
        "## How it works",
        "## What the UI shows",
        "## Quickstart",
        "## Engineering choices",
        "## Evaluation notes",
        "## Limitations",
    )
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert "Streamlit" in text
    assert "video-tutor ask" in text
    assert "12 local fixture questions" in text
    assert "50.0%" in text and "66.7%" in text
    assert "not a broad video-QA benchmark claim" in text
    assert "self-authored" in text
    assert "hidden chain-of-thought" in text


def test_architecture_and_hermes_docs_exist_and_keep_ownership_boundary_clear():
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    integration = (ROOT / "docs" / "hermes-integration.md").read_text(encoding="utf-8")
    assert "Hermes owns" in architecture
    assert "This repository owns" in architecture
    assert "project plugin" in integration.lower()
    assert "Tool Search" in integration
    assert "fork" in integration.lower()
