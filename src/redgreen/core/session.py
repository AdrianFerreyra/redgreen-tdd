"""Session Manager — orchestrates a TDD session with JSON persistence."""

from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path

from redgreen.core.timer import InvalidStateError, TimerState

_DEFAULT_CONFIG_DIR = Path.home() / ".config" / "redgreen"
_STATE_FILE = "session.json"

_ACTIVE_STATES = frozenset({TimerState.RUNNING, TimerState.PAUSED})


def _format_remaining(seconds: float) -> str:
    """Format *seconds* as ``M:SS``."""
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


class Session:
    """Orchestrates a TDD session with JSON file persistence.

    State is written to ``<config_dir>/session.json`` after every mutation so
    that sessions survive across terminal invocations.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir: Path = config_dir if config_dir is not None else _DEFAULT_CONFIG_DIR
        self._state: TimerState = TimerState.IDLE
        self._duration_minutes: int = 0
        self._remaining_seconds: float = 0.0
        self._started_at: float = 0.0  # wall-clock (time.time)
        self._monotonic_ref: float = 0.0  # monotonic baseline for running sessions
        self._load()

    # -- public API ----------------------------------------------------------

    def start(self, duration_minutes: int) -> str:
        """Start a new session.  Raises :class:`InvalidStateError` if already active."""
        if self._effective_state() in _ACTIVE_STATES:
            raise InvalidStateError(f"start() is not valid from {self._state.value} state")
        self._duration_minutes = duration_minutes
        self._remaining_seconds = duration_minutes * 60.0
        self._begin_running()
        return f"Session started: {duration_minutes} minutes"

    def status(self) -> tuple[str, int]:
        """Return ``(message, exit_code)``."""
        state = self._effective_state()
        if state == TimerState.RUNNING:
            return f"{_format_remaining(self._get_remaining())} remaining", 0
        if state == TimerState.PAUSED:
            return f"{_format_remaining(self._remaining_seconds)} remaining (paused)", 0
        if state == TimerState.EXPIRED:
            return "Session expired", 1
        return "No active session", 1

    def pause(self) -> str:
        """Pause the running session."""
        remaining = self._get_remaining()
        self._remaining_seconds = remaining
        self._state = TimerState.PAUSED
        self._started_at = time.time()
        self._save()
        return f"Session paused at {_format_remaining(remaining)} remaining"

    def resume(self) -> str:
        """Resume a paused session."""
        self._begin_running()
        return f"Session resumed: {_format_remaining(self._remaining_seconds)} remaining"

    def restart(self) -> str:
        """Restart with the original duration."""
        self._remaining_seconds = self._duration_minutes * 60.0
        self._begin_running()
        return f"Session restarted: {self._duration_minutes} minutes"

    # -- private helpers -----------------------------------------------------

    def _begin_running(self) -> None:
        """Record timestamps, transition to RUNNING, and persist."""
        self._started_at = time.time()
        self._monotonic_ref = time.monotonic()
        self._state = TimerState.RUNNING
        self._save()

    def _effective_state(self) -> TimerState:
        """Return the current state, auto-expiring a running session if needed."""
        if self._state == TimerState.RUNNING and self._get_remaining() <= 0.0:
            self._state = TimerState.EXPIRED
        return self._state

    def _get_remaining(self) -> float:
        """Compute remaining seconds for the current session."""
        if self._state != TimerState.RUNNING:
            return self._remaining_seconds
        elapsed = time.monotonic() - self._monotonic_ref
        return max(self._remaining_seconds - elapsed, 0.0)

    # -- persistence ---------------------------------------------------------

    def _save(self) -> None:
        """Write current state to the JSON file with file locking."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state": self._state.value,
            "duration_minutes": self._duration_minutes,
            "remaining_seconds": self._remaining_seconds,
            "started_at": self._started_at,
        }
        with open(self._config_dir / _STATE_FILE, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(data, f)

    def _load(self) -> None:
        """Load state from the JSON file if it exists."""
        path = self._config_dir / _STATE_FILE
        if not path.exists():
            return

        with open(path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)

        self._duration_minutes = data.get("duration_minutes", 0)
        self._remaining_seconds = data.get("remaining_seconds", 0.0)
        self._started_at = data.get("started_at", 0.0)
        raw_state = data.get("state", "idle")

        if raw_state == "running":
            elapsed = time.time() - self._started_at
            adjusted = self._remaining_seconds - elapsed
            if adjusted <= 0.0:
                self._state = TimerState.EXPIRED
                self._remaining_seconds = 0.0
            else:
                self._state = TimerState.RUNNING
                self._remaining_seconds = adjusted
                self._monotonic_ref = time.monotonic()
        elif raw_state == "paused":
            self._state = TimerState.PAUSED
        elif raw_state == "expired":
            self._state = TimerState.EXPIRED
