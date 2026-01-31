"""Timer core — a pure state-machine countdown timer."""

import time
from enum import Enum


class TimerState(Enum):
    """Possible states of the timer."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    EXPIRED = "expired"


class InvalidStateError(Exception):
    """Raised when an invalid state transition is attempted."""


_VALID_START_STATES = frozenset({TimerState.IDLE, TimerState.EXPIRED})
_VALID_RESTART_STATES = frozenset({TimerState.RUNNING, TimerState.PAUSED, TimerState.EXPIRED})

_MIN_DURATION = 1
_MAX_DURATION = 60


class Timer:
    """A pure state-machine timer that counts down from a given duration.

    Uses ``time.monotonic()`` for elapsed-time calculation so the timer is
    immune to system clock changes.  Contains no I/O, no threads, and no
    persistence -- it is a simple state machine.
    """

    def __init__(self) -> None:
        self._state: TimerState = TimerState.IDLE
        self._duration_seconds: float = 0.0
        self._original_duration_minutes: int = 0
        self._start_time: float = 0.0
        self._remaining_at_pause: float = 0.0

    # -- public interface ----------------------------------------------------

    def start(self, duration_minutes: int) -> None:
        """Start the timer for *duration_minutes* minutes (1--60).

        Valid only from IDLE or EXPIRED states.
        """
        if not isinstance(duration_minutes, int):
            raise TypeError(
                f"duration_minutes must be an integer, got {type(duration_minutes).__name__}"
            )
        if not (_MIN_DURATION <= duration_minutes <= _MAX_DURATION):
            raise ValueError(
                f"duration_minutes must be between {_MIN_DURATION} and {_MAX_DURATION}, "
                f"got {duration_minutes}"
            )
        self._require_state("start", _VALID_START_STATES)

        self._original_duration_minutes = duration_minutes
        self._duration_seconds = duration_minutes * 60.0
        self._begin_running()

    def pause(self) -> None:
        """Pause the running timer, freezing the remaining time.

        Valid only from RUNNING state.
        """
        # Trigger automatic expiration check before validating state so that
        # an already-expired timer raises InvalidStateError(expired), not a
        # confusing error about pausing while running.
        self.get_remaining()
        self._require_state("pause", frozenset({TimerState.RUNNING}))

        elapsed = time.monotonic() - self._start_time
        self._remaining_at_pause = max(self._duration_seconds - elapsed, 0.0)
        self._state = TimerState.PAUSED

    def resume(self) -> None:
        """Resume a paused timer, continuing the countdown.

        Valid only from PAUSED state.
        """
        self._require_state("resume", frozenset({TimerState.PAUSED}))

        # The frozen remaining seconds become the new effective duration.
        self._duration_seconds = self._remaining_at_pause
        self._begin_running()

    def restart(self) -> None:
        """Restart the timer with the original duration.

        Valid from RUNNING, PAUSED, or EXPIRED states.
        """
        self._require_state("restart", _VALID_RESTART_STATES)

        self._duration_seconds = self._original_duration_minutes * 60.0
        self._begin_running()

    def get_remaining(self) -> float:
        """Return the remaining time in seconds.

        Returns 0.0 when the timer is IDLE or EXPIRED.  Automatically
        transitions to EXPIRED when the remaining time reaches 0.
        """
        if self._state == TimerState.RUNNING:
            remaining = self._duration_seconds - (time.monotonic() - self._start_time)
            if remaining <= 0.0:
                self._remaining_at_pause = 0.0
                self._state = TimerState.EXPIRED
                return 0.0
            return remaining
        if self._state == TimerState.PAUSED:
            return self._remaining_at_pause
        # IDLE or EXPIRED
        return 0.0

    def get_state(self) -> TimerState:
        """Return the current timer state."""
        return self._state

    def get_original_duration(self) -> int:
        """Return the original duration in minutes."""
        return self._original_duration_minutes

    # -- private helpers -----------------------------------------------------

    def _require_state(self, method: str, valid: frozenset[TimerState]) -> None:
        """Raise ``InvalidStateError`` if the current state is not in *valid*."""
        if self._state not in valid:
            raise InvalidStateError(f"{method}() is not valid from {self._state.value} state")

    def _begin_running(self) -> None:
        """Record the start time and enter the RUNNING state."""
        self._start_time = time.monotonic()
        self._state = TimerState.RUNNING
