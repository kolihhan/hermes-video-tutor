from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_readme_has_30_second_product_story_and_honest_evaluation_language():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "video tutor" in lower and "hermes" in lower
    headings = (
        "## Agent flow",
        "## Why visual tools matter",
        "## Example traces",
        "## Quickstart",
        "## Evaluation design",
        "## Live evaluation status",
        "## Design decisions",
        "## Architecture",
        "## Limitations",
    )
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert "Streamlit" in text
    assert "video-tutor ask" in text
    assert "not a live Hermes benchmark" in text
    assert "not a valid performance conclusion" in text
    assert "hidden chain-of-thought" in text
    assert "Tool Search" in text


def test_architecture_and_hermes_docs_exist_and_keep_ownership_boundary_clear():
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    integration = (ROOT / "docs" / "hermes-integration.md").read_text(encoding="utf-8")
    assert "Hermes owns" in architecture
    assert "This repository owns" in architecture
    assert "project plugin" in integration.lower()
    assert "Tool Search" in integration
    assert "fork" in integration.lower()
