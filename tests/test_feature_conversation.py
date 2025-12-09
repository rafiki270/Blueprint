import json
from datetime import datetime
from pathlib import Path

from blueprint.state.feature import Feature


def test_conversation_round_trip(tmp_path: Path) -> None:
    feature = Feature("demo")
    feature.base_dir = tmp_path / "feature"
    feature.initialize()
    feature.clear_task_conversation("task-1")

    # Append a couple of turns
    feature.append_task_conversation("task-1", "user", "hello")
    feature.append_task_conversation("task-1", "assistant", "hi")

    entries = feature.load_task_conversation_entries("task-1")
    assert len(entries) == 2
    assert entries[0]["role"] == "user"
    assert entries[0]["content"] == "hello"
    assert entries[1]["role"] == "assistant"
    assert entries[1]["content"] == "hi"

    # Ensure JSON on disk is valid and includes entries
    data = json.loads((feature.task_conversation_path("task-1")).read_text())
    assert isinstance(data.get("entries"), list)


def test_clear_task_conversation(tmp_path: Path) -> None:
    feature = Feature("demo")
    feature.base_dir = tmp_path / "feature"
    feature.initialize()

    feature.append_task_conversation("task-1", "user", "hello")
    assert feature.load_task_conversation_entries("task-1")

    feature.clear_task_conversation("task-1")
    assert feature.load_task_conversation_entries("task-1") == []


def test_legacy_line_parsing(tmp_path: Path) -> None:
    feature = Feature("demo")
    feature.base_dir = tmp_path / "feature"
    feature.initialize()

    path = feature.task_conversation_path("task-1")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[2025-01-01] user: legacy format\n", encoding="utf-8")

    entries = feature.load_task_conversation_entries("task-1")
    assert entries[0]["role"] == "user"
    assert entries[0]["content"] == "legacy format"
