from pathlib import Path

from blueprint.interactive.prompt_history import PromptHistory


def test_prompt_history_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    store = PromptHistory(path)

    # Initially empty
    assert store.load() == []

    # Append prompts
    store.append("first")
    store.append("second")
    assert store.load() == ["first", "second"]

    # Clear
    store.clear()
    assert store.load() == []
