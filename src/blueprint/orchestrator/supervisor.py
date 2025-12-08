"""Supervision utilities for Codex-based review and corrections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models.router import ModelRole, ModelRouter
from ..state.tasks import Task


class Supervisor:
    """Coordinates GPT Codex supervision of task execution."""

    def __init__(self, router: ModelRouter, feature_dir: Path) -> None:
        self.router = router
        self.feature_dir = feature_dir
        self.codex = None

    async def initialize(self) -> None:
        """Initialize Codex connection."""
        self.codex = await self.router.route(ModelRole.REVIEWER)

    async def review_task_output(self, task: Task, output: str) -> Dict:
        """Review task output and persist the result."""
        if not self.codex:
            await self.initialize()

        result = await self.codex.review_code(output, task.description)

        review_file = self.feature_dir / "partial" / f"{task.id}_review.json"
        review_file.parent.mkdir(parents=True, exist_ok=True)
        review_file.write_text(json.dumps(result, indent=2))

        return result

    async def generate_correction(self, task: Task, output: str, issue: str) -> str:
        """Generate corrected output and persist it."""
        if not self.codex:
            await self.initialize()

        corrected = await self.codex.generate_correction(output, issue)

        correction_file = self.feature_dir / "partial" / f"{task.id}_corrected.py"
        correction_file.write_text(corrected)

        return corrected

    async def iterative_correction(self, task: Task, output: str, max_iterations: int = 3) -> Tuple[bool, str]:
        """Apply corrections iteratively until approved or max iterations reached."""
        current_output = output
        iteration = 0

        while iteration < max_iterations:
            print(f"\nIteration {iteration + 1}/{max_iterations}")

            try:
                review = await self.review_task_output(task, current_output)
            except Exception as exc:
                raise RuntimeError(f"Codex review failed: {exc}") from exc

            if review.get("approved"):
                print("✓ Output approved")
                return True, current_output

            print("✗ Corrections needed:")
            corrections = review.get("corrections", [])
            for idx, correction in enumerate(corrections, 1):
                print(f"  {idx}. {correction}")

            if corrections:
                print("\nApplying corrections...")
                current_output = await self.generate_correction(task, current_output, corrections[0])

            iteration += 1

        print("\n⚠ Max iterations reached. Manual review required.")
        return False, current_output

    async def compare_outputs(self, outputs: List[Dict]) -> Dict:
        """Compare multiple outputs and select the best one."""
        if not self.codex:
            await self.initialize()

        comparison_prompt = "Compare these outputs and select the best one:\n\n"
        for idx, item in enumerate(outputs, 1):
            comparison_prompt += f"Output {idx} (from {item['model']}):\n{item['output']}\n\n"

        comparison_prompt += (
            "Respond in JSON:\n"
            "{\n"
            '  "selected": 1,\n'
            '  "reasoning": "Why this output is best"\n'
            "}"
        )

        result_json: List[str] = []
        async for line in self.codex.execute(comparison_prompt, stream=False):
            result_json.append(line)

        return json.loads("\n".join(result_json))
