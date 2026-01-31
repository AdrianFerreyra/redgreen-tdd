"""CLI entry point for redgreen-tdd.

Uses Click to expose the ``redgreen`` command group with subcommands
that delegate to the Session manager.
"""

from __future__ import annotations

import sys
from typing import Callable, TypeVar

import click

import redgreen
from redgreen.core.session import Session
from redgreen.core.timer import InvalidStateError

T = TypeVar("T")


def _run(action: Callable[[], T]) -> T:
    """Execute *action*, converting ``InvalidStateError`` to a CLI error.

    On ``InvalidStateError`` the message is printed to stderr and the
    process exits with code 1.
    """
    try:
        return action()
    except InvalidStateError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)


@click.group()
@click.version_option(version=redgreen.__version__, prog_name="redgreen")
def cli() -> None:
    """redgreen-tdd: A TDD session timer for macOS developers."""


@cli.command()
@click.argument("minutes", type=int)
def start(minutes: int) -> None:
    """Start a TDD session for MINUTES minutes."""
    session = Session()
    message = _run(lambda: session.start(minutes))
    click.echo(message)


@cli.command()
def status() -> None:
    """Show the current session status."""
    session = Session()
    message, exit_code = session.status()
    click.echo(message)
    sys.exit(exit_code)


@cli.command()
def pause() -> None:
    """Pause the current session."""
    session = Session()
    message = _run(session.pause)
    click.echo(message)


@cli.command()
def resume() -> None:
    """Resume a paused session."""
    session = Session()
    message = _run(session.resume)
    click.echo(message)


@cli.command()
def restart() -> None:
    """Restart the session with the original duration."""
    session = Session()
    message = _run(session.restart)
    click.echo(message)
