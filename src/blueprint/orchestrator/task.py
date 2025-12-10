"""Task & workflow coordination matching orchestrator design spec."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Sequence

from ..models.base import ChatResponse


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskStep:
    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    suggested_approach: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None


@dataclass
class Task:
    name: str
    description: str
    steps: list[TaskStep]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    task: Task
    success: bool
    outputs: dict[str, Any]
    errors: list[str]


class TaskCoordinator:
    """Coordinates multi-step task execution."""

    def __init__(self, orchestrator: "LLMOrchestrator") -> None:
        self.orchestrator = orchestrator

    async def execute(
        self,
        task: Task,
        backend: str | None = None,
        streaming: bool = True,  # streaming unused but kept for API parity
    ) -> TaskResult:
        outputs: dict[str, Any] = {}
        errors: list[str] = []
        completed_steps: set[str] = set()

        while len(completed_steps) < len(task.steps):
            next_step = self._find_next_step(task.steps, completed_steps)
            if not next_step:
                errors.append("Circular dependencies or blocked steps")
                break

            try:
                next_step.status = TaskStatus.IN_PROGRESS
                response: ChatResponse = await self.orchestrator.chat(
                    message=self._build_step_prompt(next_step, task.context),
                    backend=backend,
                    include_context=True,
                )
                next_step.result = response.content
                next_step.status = TaskStatus.COMPLETED
                outputs[next_step.id] = response.content
                completed_steps.add(next_step.id)
            except Exception as exc:  # noqa: PERF203
                next_step.status = TaskStatus.FAILED
                next_step.error = str(exc)
                errors.append(f"Step {next_step.id} failed: {exc}")
                break

        success = len(completed_steps) == len(task.steps)
        return TaskResult(task=task, success=success, outputs=outputs, errors=errors)

    def _find_next_step(self, steps: Sequence[TaskStep], completed: set[str]) -> Optional[TaskStep]:
        for step in steps:
            if step.id in completed:
                continue
            if all(dep in completed for dep in step.dependencies):
                return step
        return None

    def _build_step_prompt(self, step: TaskStep, context: dict[str, Any]) -> str:
        prompt = f"""
Execute the following task step:

**Step**: {step.description}

**Suggested Approach**: {step.suggested_approach}

**Context**:
{self._format_context(context)}

Provide a detailed implementation.
""".strip()
        return prompt

    def _format_context(self, context: dict[str, Any]) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in context.items())
