# Phase 5: Static Mode

## Overview
This phase implements the non-interactive static mode for automated task execution via `blueprint run <feature>`.

## Dependencies
- Phases 1, 2, and 3 must be complete

## Directory Structure
```
src/blueprint/static/
├── __init__.py
└── runner.py
```

## File: `src/blueprint/static/runner.py`
**Purpose**: Automated task execution without user interaction

**Requirements**:
1. Execute all incomplete tasks sequentially
2. Display progress indicators
3. Log all output to files
4. Handle errors gracefully
5. Provide summary report
6. Support resuming from interruption

**Implementation outline**:
```python
import asyncio
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.table import Table

from ..config import Config
from ..state.feature import Feature
from ..state.tasks import TaskManager, Task, TaskStatus
from ..models.router import ModelRouter
from ..orchestrator.executor import TaskExecutor
from ..orchestrator.supervisor import Supervisor
from ..utils.logger import Logger

class StaticRunner:
    """Runs feature tasks in automated static mode"""

    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        self.config = Config()
        self.feature = Feature(feature_name)
        self.task_manager = TaskManager(self.feature.base_dir)
        self.router = ModelRouter(self.config)
        self.executor = TaskExecutor(
            self.task_manager,
            self.router,
            self.feature.base_dir
        )
        self.supervisor = Supervisor(self.router, self.feature.base_dir)
        self.logger = Logger(self.feature.base_dir)
        self.console = Console()

        self.stats = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0
        }

    async def run(self, max_failures: int = 3):
        """
        Run all incomplete tasks

        Args:
            max_failures: Maximum consecutive failures before stopping
        """
        # Verify feature exists
        if not self.feature.exists():
            self.console.print(f"[red]Error: Feature '{self.feature_name}' not found[/red]")
            self.console.print("Run 'blueprint' to create a new feature")
            return False

        # Check model availability
        await self.router.check_availability()

        # Get incomplete tasks
        tasks = self.task_manager.get_missing()
        if not tasks:
            self.console.print("[green]All tasks completed![/green]")
            return True

        self.stats["total"] = len(tasks)

        # Print header
        self._print_header(tasks)

        # Execute tasks
        consecutive_failures = 0
        for i, task in enumerate(tasks, 1):
            self.console.print(f"\n{'='*60}")
            self.console.print(f"Task {i}/{len(tasks)}: {task.title}")
            self.console.print(f"{'='*60}")

            # Execute task
            success = await self._execute_task_with_progress(task)

            if success:
                self.stats["completed"] += 1
                consecutive_failures = 0
                self.console.print(f"[green]✓ Task completed[/green]")
            else:
                self.stats["failed"] += 1
                consecutive_failures += 1
                self.console.print(f"[red]✗ Task failed[/red]")

                if consecutive_failures >= max_failures:
                    self.console.print(f"\n[red]Stopping: {max_failures} consecutive failures[/red]")
                    break

        # Print summary
        self._print_summary()

        return self.stats["failed"] == 0

    async def _execute_task_with_progress(self, task: Task) -> bool:
        """Execute task with progress indicator"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=self.console
        ) as progress:
            task_progress = progress.add_task(
                f"Executing {task.type.value} task...",
                total=None
            )

            try:
                # Execute task
                success = await self.executor.execute_task(task)

                if success and task.type.value == "code":
                    # Review with supervisor
                    progress.update(task_progress, description="Reviewing code...")
                    success = await self._review_and_correct(task)

                return success

            except Exception as e:
                self.logger.log_error(f"Task {task.id} failed: {str(e)}")
                self.console.print(f"[red]Error: {str(e)}[/red]")
                return False

    async def _review_and_correct(self, task: Task, max_iterations: int = 2) -> bool:
        """Review task output and apply corrections"""
        # Find output file
        output_file = self.feature.base_dir / "partial" / f"{task.id}_code.py"
        if not output_file.exists():
            return True  # No output to review

        output_content = output_file.read_text()

        self.console.print("Running supervisor review...")

        # Iterative correction
        approved, final_output = await self.supervisor.iterative_correction(
            task,
            output_content,
            max_iterations=max_iterations
        )

        if approved:
            # Save final output
            output_file.write_text(final_output)
            self.console.print("[green]✓ Code approved by supervisor[/green]")
            return True
        else:
            self.console.print("[yellow]⚠ Manual review required[/yellow]")
            return False

    def _print_header(self, tasks: List[Task]):
        """Print execution header"""
        panel = Panel(
            f"""[bold]Blueprint Static Mode[/bold]

Feature: {self.feature_name}
Tasks to execute: {len(tasks)}
Logs: {self.feature.logs_dir}
""",
            title="Starting Execution",
            border_style="blue"
        )
        self.console.print(panel)

    def _print_summary(self):
        """Print execution summary"""
        table = Table(title="Execution Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="magenta")

        table.add_row("Total Tasks", str(self.stats["total"]))
        table.add_row("Completed", f"[green]{self.stats['completed']}[/green]")
        table.add_row("Failed", f"[red]{self.stats['failed']}[/red]")
        table.add_row("Skipped", str(self.stats["skipped"]))

        self.console.print("\n")
        self.console.print(table)

        if self.stats["failed"] > 0:
            self.console.print(f"\n[yellow]Check logs for details: {self.feature.logs_dir}[/yellow]")
        else:
            self.console.print("\n[bold green]All tasks completed successfully![/bold green]")

    async def run_single_task(self, task_id: str) -> bool:
        """
        Run a single task by ID

        Args:
            task_id: Task ID to execute

        Returns:
            True if successful
        """
        task = self.task_manager.get(task_id)
        if not task:
            self.console.print(f"[red]Error: Task '{task_id}' not found[/red]")
            return False

        await self.router.check_availability()

        self.console.print(f"Executing task: {task.title}")

        success = await self._execute_task_with_progress(task)

        if success:
            self.console.print(f"[green]✓ Task completed[/green]")
        else:
            self.console.print(f"[red]✗ Task failed[/red]")

        return success

    async def resume(self):
        """Resume from last incomplete task"""
        current_task_file = self.feature.base_dir / "current_task.txt"

        if current_task_file.exists():
            task_id = current_task_file.read_text().strip()
            task = self.task_manager.get(task_id)

            if task and task.status != TaskStatus.COMPLETED:
                self.console.print(f"[yellow]Resuming from task: {task.title}[/yellow]")

                # Get remaining tasks starting from current
                all_tasks = self.task_manager.list_all()
                task_index = next(
                    (i for i, t in enumerate(all_tasks) if t.id == task_id),
                    None
                )

                if task_index is not None:
                    remaining_tasks = [
                        t for t in all_tasks[task_index:]
                        if t.status != TaskStatus.COMPLETED
                    ]
                    self.stats["total"] = len(remaining_tasks)

                    for task in remaining_tasks:
                        success = await self._execute_task_with_progress(task)
                        if success:
                            self.stats["completed"] += 1
                        else:
                            self.stats["failed"] += 1

                    self._print_summary()
                    return self.stats["failed"] == 0

        # No resume point, run normally
        return await self.run()


def run_static_mode(feature_name: str, task_id: Optional[str] = None):
    """
    Entry point for static mode

    Args:
        feature_name: Name of feature to execute
        task_id: Optional specific task to run
    """
    runner = StaticRunner(feature_name)

    if task_id:
        return asyncio.run(runner.run_single_task(task_id))
    else:
        return asyncio.run(runner.run())
```

## File: `src/blueprint/static/__init__.py`
```python
"""Static mode runner"""

from .runner import StaticRunner, run_static_mode

__all__ = ["StaticRunner", "run_static_mode"]
```

## Update: `src/blueprint/cli.py`
Add static mode command:

```python
@main.command()
@click.argument('feature')
@click.option('--task', '-t', help='Run specific task only')
def run(feature, task):
    """Run feature in static mode"""
    from .static import run_static_mode

    success = run_static_mode(feature, task_id=task)
    sys.exit(0 if success else 1)
```

## Usage Examples

```bash
# Run all incomplete tasks
blueprint run my-feature

# Run specific task
blueprint run my-feature --task task-3

# Resume from interruption
blueprint run my-feature
```

## Testing Checklist
- [ ] Static mode executes all tasks sequentially
- [ ] Progress indicators display correctly
- [ ] Output is logged to files
- [ ] Summary report is accurate
- [ ] Failures are handled gracefully
- [ ] Max consecutive failures stops execution
- [ ] Single task execution works
- [ ] Resume functionality works
- [ ] Exit codes are correct (0 success, 1 failure)

## Dependencies
Add to requirements/pyproject.toml:
- rich >= 13.0.0

## Success Criteria
- Can execute full feature pipeline non-interactively
- Progress is clearly visible
- All output is logged
- Failures don't crash the process
- Summary provides actionable information
- Can be used in CI/CD pipelines
- Exit codes properly indicate success/failure
