"""Task execution orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models.router import ModelRole, ModelRouter
from ..state.tasks import Task, TaskManager, TaskStatus, TaskType
from ..utils.logger import Logger


class TaskExecutor:
    """Executes individual tasks using appropriate LLM models."""

    def __init__(self, task_manager: TaskManager, router: ModelRouter, feature_dir: Path) -> None:
        self.task_manager = task_manager
        self.router = router
        self.feature_dir = feature_dir
        self.logger = Logger(feature_dir)
        self.current_task: Optional[Task] = None

    async def execute_task(self, task: Task) -> bool:
        """
        Execute a single task.

        Returns:
            True if successful, False otherwise.
        """
        self.current_task = task
        self.task_manager.mark_in_progress(task.id)
        self.logger.log_task_start(task)

        print(f"\n{'=' * 60}")
        print(f"Executing: {task.title}")
        print(f"Type: {task.type.value}")
        print(f"{'=' * 60}\n")

        try:
            if task.type == TaskType.ARCHITECTURE:
                result = await self._execute_architecture_task(task)
            elif task.type == TaskType.BOILERPLATE:
                result = await self._execute_boilerplate_task(task)
            elif task.type == TaskType.CODE:
                result = await self._execute_code_task(task)
            elif task.type == TaskType.REVIEW:
                result = await self._execute_review_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.type}")

            if result:
                self.task_manager.mark_done(task.id)
                self.logger.log_task_complete(task)
                print(f"\n✓ Task completed: {task.title}")
            else:
                self.logger.log_task_failed(task, "Execution returned False")
                print(f"\n✗ Task failed: {task.title}")

            return result

        except Exception as exc:
            self.logger.log_task_failed(task, str(exc))
            print(f"\n✗ Task failed with error: {exc}")
            return False
        finally:
            self.current_task = None

    async def _execute_architecture_task(self, task: Task) -> bool:
        """Execute architecture/design task."""
        claude = await self.router.route(ModelRole.ARCHITECT)

        prompt = f"""Architecture task: {task.title}

Description:
{task.description}

Provide detailed architectural guidance, design decisions, and implementation approach."""

        output_lines = []
        async for line in claude.execute(prompt):
            print(line)
            output_lines.append(line)

        output_file = self.feature_dir / "partial" / f"{task.id}_architecture.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(output_lines))
        return True

    async def _execute_boilerplate_task(self, task: Task) -> bool:
        """Execute boilerplate generation task."""
        gemini = await self.router.route(ModelRole.BOILERPLATE)

        output_lines = []
        async for line in gemini.generate_boilerplate(task.description):
            print(line)
            output_lines.append(line)

        output_file = self.feature_dir / "partial" / f"{task.id}_boilerplate.py"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(output_lines))
        print(f"\nBoilerplate saved to {output_file}")
        return True

    async def _execute_code_task(self, task: Task) -> bool:
        """Execute code generation task."""
        spec_file = self.feature_dir / "spec.md"
        context = spec_file.read_text(encoding="utf-8") if spec_file.exists() else ""

        coder = await self.router.route(ModelRole.CODER, content_size=len(context))

        output_lines = []
        async for line in coder.generate_code(task.description, context):
            print(line)
            output_lines.append(line)

        output_file = self.feature_dir / "partial" / f"{task.id}_code.py"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(output_lines))
        print(f"\nCode saved to {output_file}")
        return True

    async def _execute_review_task(self, task: Task) -> bool:
        """Execute code review task."""
        codex = await self.router.route(ModelRole.REVIEWER)

        code_files = list((self.feature_dir / "partial").glob("*_code.py"))
        if not code_files:
            print("No code files found to review")
            return False

        for code_file in code_files:
            code = code_file.read_text(encoding="utf-8")
            print(f"\nReviewing {code_file.name}...")

            review_result = await codex.review_code(code, task.description)

            if review_result.get("approved"):
                print("✓ Code approved")
            else:
                print("✗ Code needs corrections:")
                print(review_result.get("feedback"))

                review_file = self.feature_dir / "partial" / f"{code_file.stem}_review.json"
                review_file.write_text(json.dumps(review_result, indent=2))

        return True

    async def stop_current_task(self) -> None:
        """Stop currently executing task (placeholder)."""
        if self.current_task:
            print(f"\nStopping task: {self.current_task.title}")
            self.current_task = None

    def get_current_task(self) -> Optional[Task]:
        """Get currently executing task."""
        return self.current_task
