"""Blueprint CLI entry point."""

from __future__ import annotations

import click

from . import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Blueprint - Multi-LLM Development Orchestrator."""
    pass


@main.command()
def interactive() -> None:
    """Start interactive mode (placeholder for Phase 4)."""
    click.echo("Interactive mode - Coming in Phase 4")


@main.command()
@click.argument("feature")
def run(feature: str) -> None:
    """Run feature in static mode."""
    click.echo(f"Static mode for {feature} - Coming in Phase 5")


if __name__ == "__main__":
    main()
