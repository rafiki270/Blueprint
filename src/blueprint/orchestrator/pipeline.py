"""Brief → Spec → Tasks pipeline orchestration."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models.router import ModelRole, ModelRouter
from ..state.feature import Feature
from ..state.tasks import TaskManager, TaskType


class Pipeline:
    """Orchestrates the brief → spec → tasks pipeline."""

    def __init__(self, feature: Feature, router: ModelRouter) -> None:
        self.feature = feature
        self.router = router
        self.task_manager = TaskManager(feature.base_dir)

    async def process_brief(self, brief: str, skip_spec: bool = False) -> str:
        """
        Process user brief into specification.

        Args:
            brief: User's feature description.
            skip_spec: If True, treat brief as the spec directly.
        """
        if skip_spec:
            spec = brief
        else:
            print("Generating specification using Claude...")
            claude = await self.router.route(ModelRole.ARCHITECT)

            spec = await claude.generate_spec(brief)
            print(spec)

        self.feature.save_spec(spec)
        print(f"\nSpecification saved to {self.feature.spec_file}")
        return spec

    async def spec_to_tasks(self, spec: Optional[str] = None) -> List[Dict]:
        """
        Convert specification to structured tasks.

        Args:
            spec: Specification text (loads from file if None).
        """
        if spec is None:
            spec = self.feature.load_spec()
            if not spec:
                raise ValueError("No specification found")

        spec_size = len(spec)
        print(f"Specification size: {spec_size} chars")

        parser = await self.router.route(ModelRole.PARSER, content_size=spec_size)
        print(f"Using {parser.__class__.__name__} for task generation...")

        tasks_json = await parser.parse_spec_to_tasks(spec)

        try:
            tasks_data = json.loads(tasks_json)
        except json.JSONDecodeError as exc:
            print(f"ERROR: Failed to parse tasks JSON: {exc}")
            print("Raw output:")
            print(tasks_json)
            raise

        # Review with Codex supervisor
        print("\nReviewing tasks with Codex supervisor...")
        codex = await self.router.route(ModelRole.REVIEWER)
        refined_json = await codex.review_tasks(json.dumps(tasks_data, indent=2))

        try:
            tasks_data = json.loads(refined_json)
        except json.JSONDecodeError:
            print("WARNING: Supervisor refinement failed, using original tasks")

        # Create tasks in task manager
        for task_dict in tasks_data if isinstance(tasks_data, list) else []:
            raw_type = task_dict.get("type", "code")
            try:
                task_type = TaskType(raw_type)
            except ValueError:
                task_type = TaskType.CODE

            self.task_manager.create(
                title=task_dict.get("title", "Task"),
                description=task_dict.get("description", ""),
                type=task_type,
            )

        self.task_manager.save()
        print(f"\n{len(self.task_manager.tasks)} tasks created")
        return tasks_data if isinstance(tasks_data, list) else []

    async def run_full_pipeline(self, brief: str, skip_spec: bool = False) -> None:
        """Run complete pipeline: brief → spec → tasks."""
        print("=" * 60)
        print("BLUEPRINT PIPELINE")
        print("=" * 60)

        await self.router.check_availability()

        print("\n[1/2] Generating specification...")
        spec = await self.process_brief(brief, skip_spec=skip_spec)

        print("\n[2/2] Converting specification to tasks...")
        tasks = await self.spec_to_tasks(spec)

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Feature: {self.feature.name}")
        print(f"Spec: {self.feature.spec_file}")
        print(f"Tasks: {len(tasks)}")
        print("\nRun 'blueprint' for interactive mode or")
        print(f"'blueprint run {self.feature.name}' for static mode")

    @staticmethod
    async def from_brief_file(brief_path: Path, feature_name: str, config) -> Tuple["Pipeline", str]:
        """Create pipeline from brief file."""
        brief = brief_path.read_text(encoding="utf-8")

        feature = Feature(feature_name)
        feature.initialize()

        router = ModelRouter(config)
        pipeline = Pipeline(feature, router)
        return pipeline, brief

    @staticmethod
    async def from_stdin(feature_name: str, config) -> Tuple["Pipeline", str]:
        """Create pipeline from stdin input."""
        print("Paste your feature brief (press Ctrl+D when done):")
        print("-" * 60)

        import sys

        brief = sys.stdin.read()

        feature = Feature(feature_name)
        feature.initialize()

        router = ModelRouter(config)
        pipeline = Pipeline(feature, router)
        return pipeline, brief
