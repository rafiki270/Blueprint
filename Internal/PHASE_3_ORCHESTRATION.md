# Phase 3: Orchestration Pipeline

## Overview
This phase implements the core orchestration logic: Brief → Spec → Tasks → Code execution pipeline.

## Dependencies
- Phase 1 (Foundation) must be complete
- Phase 2 (LLM Wrappers) must be complete

## Directory Structure
```
src/blueprint/orchestrator/
├── __init__.py
├── pipeline.py
├── executor.py
└── supervisor.py
```

## File: `src/blueprint/orchestrator/pipeline.py`
**Purpose**: Coordinate the Brief → Spec → Tasks workflow

**Requirements**:
1. Accept brief from multiple sources (file, stdin, paste)
2. Generate spec using Claude
3. Convert spec to tasks using DeepSeek or Gemini (based on size)
4. Refine tasks using Codex supervisor
5. Save all artifacts to feature directory

**Implementation outline**:
```python
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from ..models.router import ModelRouter, ModelRole
from ..state.feature import Feature
from ..state.tasks import TaskManager, TaskType
import json

class Pipeline:
    """Orchestrates the brief → spec → tasks → code pipeline"""

    def __init__(self, feature: Feature, router: ModelRouter):
        self.feature = feature
        self.router = router
        self.task_manager = TaskManager(feature.base_dir)

    async def process_brief(self, brief: str, skip_spec: bool = False) -> str:
        """
        Process user brief into specification

        Args:
            brief: User's feature description
            skip_spec: If True, treat brief as the spec directly

        Returns:
            Generated or provided specification
        """
        if skip_spec:
            # User provided spec directly
            spec = brief
        else:
            # Generate spec using Claude (Architect)
            print("Generating specification using Claude...")
            claude = await self.router.route(ModelRole.ARCHITECT)

            spec_lines = []
            async for line in claude.generate_spec(brief):
                print(line)
                spec_lines.append(line)

            spec = "\n".join(spec_lines)

        # Save spec
        self.feature.save_spec(spec)
        print(f"\nSpecification saved to {self.feature.spec_file}")

        return spec

    async def spec_to_tasks(self, spec: Optional[str] = None) -> List[Dict]:
        """
        Convert specification to structured tasks

        Args:
            spec: Specification text (loads from file if None)

        Returns:
            List of task dictionaries
        """
        if spec is None:
            spec = self.feature.load_spec()
            if not spec:
                raise ValueError("No specification found")

        spec_size = len(spec)
        print(f"Specification size: {spec_size} chars")

        # Route to appropriate model for parsing
        parser = await self.router.route(ModelRole.PARSER, content_size=spec_size)
        print(f"Using {parser.__class__.__name__} for task generation...")

        # Generate tasks
        tasks_json = await parser.parse_spec_to_tasks(spec)

        # Parse JSON
        try:
            tasks_data = json.loads(tasks_json)
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse tasks JSON: {e}")
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
        for task_dict in tasks_data:
            task_type = TaskType[task_dict.get("type", "code").upper()]
            self.task_manager.create(
                title=task_dict["title"],
                description=task_dict.get("description", ""),
                type=task_type
            )

        self.task_manager.save()
        print(f"\n{len(tasks_data)} tasks created")

        return tasks_data

    async def run_full_pipeline(self, brief: str, skip_spec: bool = False):
        """
        Run complete pipeline: brief → spec → tasks

        Args:
            brief: User's feature brief or spec
            skip_spec: If True, treat brief as spec directly
        """
        print("=" * 60)
        print("BLUEPRINT PIPELINE")
        print("=" * 60)

        # Check model availability
        await self.router.check_availability()

        # Step 1: Brief → Spec
        print("\n[1/2] Generating specification...")
        spec = await self.process_brief(brief, skip_spec=skip_spec)

        # Step 2: Spec → Tasks
        print("\n[2/2] Converting specification to tasks...")
        tasks = await self.spec_to_tasks(spec)

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Feature: {self.feature.name}")
        print(f"Spec: {self.feature.spec_file}")
        print(f"Tasks: {len(tasks)}")
        print("\nRun 'blueprint' to start interactive mode")
        print(f"Or 'blueprint run {self.feature.name}' for static mode")

    @staticmethod
    async def from_brief_file(brief_path: Path, feature_name: str, config) -> 'Pipeline':
        """Create pipeline from brief file"""
        with open(brief_path, 'r') as f:
            brief = f.read()

        feature = Feature(feature_name)
        feature.initialize()

        router = ModelRouter(config)
        pipeline = Pipeline(feature, router)

        return pipeline, brief

    @staticmethod
    async def from_stdin(feature_name: str, config) -> 'Pipeline':
        """Create pipeline from stdin input"""
        print("Paste your feature brief (press Ctrl+D when done):")
        print("-" * 60)

        import sys
        brief = sys.stdin.read()

        feature = Feature(feature_name)
        feature.initialize()

        router = ModelRouter(config)
        pipeline = Pipeline(feature, router)

        return pipeline, brief
```

## File: `src/blueprint/orchestrator/executor.py`
**Purpose**: Execute individual tasks with appropriate models

**Requirements**:
1. Execute task based on type (code, boilerplate, review)
2. Route to appropriate model
3. Stream output to logs
4. Handle task state transitions
5. Apply generated code/patches
6. Retry logic on failures

**Implementation outline**:
```python
import asyncio
from typing import Optional, Dict
from pathlib import Path
from ..models.router import ModelRouter, ModelRole
from ..state.tasks import Task, TaskManager, TaskStatus, TaskType
from ..utils.logger import Logger

class TaskExecutor:
    """Executes individual tasks using appropriate LLM models"""

    def __init__(self, task_manager: TaskManager, router: ModelRouter,
                 feature_dir: Path):
        self.task_manager = task_manager
        self.router = router
        self.feature_dir = feature_dir
        self.logger = Logger(feature_dir)
        self.current_task: Optional[Task] = None

    async def execute_task(self, task: Task) -> bool:
        """
        Execute a single task

        Args:
            task: Task to execute

        Returns:
            True if successful, False otherwise
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

        except Exception as e:
            self.logger.log_task_failed(task, str(e))
            print(f"\n✗ Task failed with error: {str(e)}")
            return False

        finally:
            self.current_task = None

    async def _execute_architecture_task(self, task: Task) -> bool:
        """Execute architecture/design task"""
        # These tasks are typically manual or require Claude
        claude = await self.router.route(ModelRole.ARCHITECT)

        prompt = f"""Architecture task: {task.title}

Description:
{task.description}

Provide detailed architectural guidance, design decisions, and implementation approach."""

        output_lines = []
        async for line in claude.execute(prompt):
            print(line)
            output_lines.append(line)

        # Save output
        output_file = self.feature_dir / "partial" / f"{task.id}_architecture.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(output_lines))

        return True

    async def _execute_boilerplate_task(self, task: Task) -> bool:
        """Execute boilerplate generation task"""
        gemini = await self.router.route(ModelRole.BOILERPLATE)

        output_lines = []
        async for line in gemini.generate_boilerplate(task.description):
            print(line)
            output_lines.append(line)

        # Save generated code
        output_file = self.feature_dir / "partial" / f"{task.id}_boilerplate.py"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(output_lines))

        print(f"\nBoilerplate saved to {output_file}")
        return True

    async def _execute_code_task(self, task: Task) -> bool:
        """Execute code generation task"""
        # Get context from spec
        spec_file = self.feature_dir / "spec.md"
        context = spec_file.read_text() if spec_file.exists() else ""

        # Route to coder (DeepSeek or Gemini)
        coder = await self.router.route(ModelRole.CODER, content_size=len(context))

        output_lines = []
        async for line in coder.generate_code(task.description, context):
            print(line)
            output_lines.append(line)

        # Save generated code
        output_file = self.feature_dir / "partial" / f"{task.id}_code.py"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(output_lines))

        print(f"\nCode saved to {output_file}")
        return True

    async def _execute_review_task(self, task: Task) -> bool:
        """Execute code review task"""
        codex = await self.router.route(ModelRole.REVIEWER)

        # Find code to review
        code_files = list((self.feature_dir / "partial").glob("*_code.py"))
        if not code_files:
            print("No code files found to review")
            return False

        for code_file in code_files:
            code = code_file.read_text()
            print(f"\nReviewing {code_file.name}...")

            review_result = await codex.review_code(code, task.description)

            if review_result.get("approved"):
                print("✓ Code approved")
            else:
                print("✗ Code needs corrections:")
                print(review_result.get("feedback"))

                # Save review
                review_file = self.feature_dir / "partial" / f"{code_file.stem}_review.json"
                import json
                review_file.write_text(json.dumps(review_result, indent=2))

        return True

    async def stop_current_task(self):
        """Stop currently executing task"""
        if self.current_task:
            print(f"\nStopping task: {self.current_task.title}")
            # Stop any running LLM process
            # This will be handled by the interactive mode
            self.current_task = None

    def get_current_task(self) -> Optional[Task]:
        """Get currently executing task"""
        return self.current_task
```

## File: `src/blueprint/orchestrator/supervisor.py`
**Purpose**: Coordinate GPT Codex supervision and corrections

**Requirements**:
1. Review generated code/tasks
2. Generate corrections
3. Apply corrections iteratively
4. Mediate between DeepSeek and Gemini outputs
5. Approve/reject completions

**Implementation outline**:
```python
import asyncio
import json
from typing import Dict, List, Optional
from pathlib import Path
from ..models.router import ModelRouter, ModelRole
from ..state.tasks import Task

class Supervisor:
    """Coordinates GPT Codex supervision of task execution"""

    def __init__(self, router: ModelRouter, feature_dir: Path):
        self.router = router
        self.feature_dir = feature_dir
        self.codex = None

    async def initialize(self):
        """Initialize Codex connection"""
        self.codex = await self.router.route(ModelRole.REVIEWER)

    async def review_task_output(self, task: Task, output: str) -> Dict:
        """
        Review task output

        Args:
            task: The completed task
            output: Generated output (code, docs, etc.)

        Returns:
            Review result with approval status and feedback
        """
        if not self.codex:
            await self.initialize()

        result = await self.codex.review_code(output, task.description)

        # Save review
        review_file = self.feature_dir / "partial" / f"{task.id}_review.json"
        review_file.parent.mkdir(parents=True, exist_ok=True)
        review_file.write_text(json.dumps(result, indent=2))

        return result

    async def generate_correction(self, task: Task, output: str, issue: str) -> str:
        """
        Generate corrected output

        Args:
            task: The task being corrected
            output: Original output
            issue: Issue description from review

        Returns:
            Corrected output
        """
        if not self.codex:
            await self.initialize()

        corrected = await self.codex.generate_correction(output, issue)

        # Save correction
        correction_file = self.feature_dir / "partial" / f"{task.id}_corrected.py"
        correction_file.write_text(corrected)

        return corrected

    async def iterative_correction(self, task: Task, output: str,
                                   max_iterations: int = 3) -> tuple[bool, str]:
        """
        Apply corrections iteratively until approved

        Args:
            task: The task being corrected
            output: Initial output
            max_iterations: Maximum correction attempts

        Returns:
            (approved, final_output)
        """
        current_output = output
        iteration = 0

        while iteration < max_iterations:
            print(f"\nIteration {iteration + 1}/{max_iterations}")

            review = await self.review_task_output(task, current_output)

            if review.get("approved"):
                print("✓ Output approved")
                return True, current_output

            print("✗ Corrections needed:")
            corrections = review.get("corrections", [])
            for i, correction in enumerate(corrections, 1):
                print(f"  {i}. {correction}")

            # Apply first correction
            if corrections:
                print("\nApplying corrections...")
                current_output = await self.generate_correction(
                    task, current_output, corrections[0]
                )

            iteration += 1

        print(f"\n⚠ Max iterations reached. Manual review required.")
        return False, current_output

    async def compare_outputs(self, outputs: List[Dict]) -> Dict:
        """
        Compare multiple outputs and select best

        Args:
            outputs: List of {model: str, output: str} dicts

        Returns:
            Best output with reasoning
        """
        if not self.codex:
            await self.initialize()

        comparison_prompt = f"""Compare these outputs and select the best one:

"""
        for i, item in enumerate(outputs, 1):
            comparison_prompt += f"""
Output {i} (from {item['model']}):
{item['output']}

"""

        comparison_prompt += """
Respond in JSON:
{
  "selected": 1,
  "reasoning": "Why this output is best"
}"""

        result_json = []
        async for line in self.codex.execute(comparison_prompt, stream=False):
            result_json.append(line)

        result = json.loads("\n".join(result_json))
        return result
```

## File: `src/blueprint/orchestrator/__init__.py`
```python
"""Orchestration components"""

from .pipeline import Pipeline
from .executor import TaskExecutor
from .supervisor import Supervisor

__all__ = ["Pipeline", "TaskExecutor", "Supervisor"]
```

## Integration Example
**How these components work together:**

```python
# In CLI or interactive mode:
from blueprint.config import Config
from blueprint.state.feature import Feature
from blueprint.models.router import ModelRouter
from blueprint.orchestrator import Pipeline, TaskExecutor, Supervisor

async def main():
    # Setup
    config = Config()
    feature = Feature("my-feature")
    feature.initialize()
    router = ModelRouter(config)

    # Run pipeline
    pipeline = Pipeline(feature, router)
    await pipeline.run_full_pipeline(brief="Add user authentication")

    # Execute tasks
    task_manager = pipeline.task_manager
    executor = TaskExecutor(task_manager, router, feature.base_dir)
    supervisor = Supervisor(router, feature.base_dir)

    # Execute all tasks
    for task in task_manager.get_missing():
        success = await executor.execute_task(task)
        if not success:
            print(f"Task {task.id} failed, review needed")

asyncio.run(main())
```

## Testing Checklist
- [ ] Pipeline can process brief from file
- [ ] Pipeline can process brief from stdin
- [ ] Spec generation works with Claude
- [ ] Tasks are created from spec
- [ ] Codex reviews and refines tasks
- [ ] Task executor routes correctly by type
- [ ] Generated code is saved to partial/ directory
- [ ] Supervisor can review outputs
- [ ] Iterative correction works
- [ ] Multiple correction attempts are logged

## Success Criteria
- Complete brief → spec → tasks pipeline works end-to-end
- Tasks are executed with appropriate models
- Task state transitions are tracked
- Generated code is organized in feature directory
- Supervisor reviews work correctly
- Errors are logged and recoverable
