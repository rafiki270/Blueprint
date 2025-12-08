"""Blueprint CLI entry point."""

from __future__ import annotations

import asyncio

import click

from . import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.option("--feature", default="default", help="Feature name to work on (default: default)")
@click.pass_context
def main(ctx: click.Context, feature: str) -> None:
    """Blueprint - Multi-LLM Development Orchestrator."""
    if ctx.invoked_subcommand is None:
        # Default to console chat mode
        try:
            from .console_chat import run_console_chat

            asyncio.run(run_console_chat(feature))
        except Exception as exc:  # pragma: no cover - defensive fallback
            click.echo(f"Unable to start console mode: {exc}")
            ctx.exit(1)


def _start_tui(feature: str) -> None:
    """Helper to launch the Textual TUI."""
    try:
        from .interactive import BlueprintApp
    except Exception as exc:  # pragma: no cover - defensive fallback
        click.echo(f"Unable to start interactive mode: {exc}")
        return

    app = BlueprintApp(feature)
    app.run()


@main.command()
@click.argument("feature", required=False, default="default")
def tui(feature: str) -> None:
    """Start Textual TUI."""
    _start_tui(feature)


@main.command()
@click.argument("feature", required=False, default="default")
def interactive(feature: str) -> None:
    """Alias for TUI mode (legacy)."""
    _start_tui(feature)


@main.command()
@click.argument("feature")
def run(feature: str) -> None:
    """Run feature in static mode."""
    click.echo(f"Static mode for {feature} - Coming in Phase 5")


if __name__ == "__main__":
    main()
