"""Comprehensive tests for the Timer state machine."""

from unittest.mock import patch

import pytest

from redgreen.core.timer import InvalidStateError, Timer, TimerState

# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestTimerInitialState:
    """A freshly-created Timer must be IDLE with no active session."""

    def test_initial_state_is_idle(self) -> None:
        timer = Timer()
        assert timer.get_state() == TimerState.IDLE

    def test_initial_remaining_is_zero(self) -> None:
        timer = Timer()
        assert timer.get_remaining() == 0.0

    def test_initial_original_duration_is_zero(self) -> None:
        timer = Timer()
        assert timer.get_original_duration() == 0


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------


class TestTimerStart:
    """start(duration_minutes) transitions IDLE -> RUNNING."""

    def test_start_transitions_to_running(self) -> None:
        timer = Timer()
        timer.start(25)
        assert timer.get_state() == TimerState.RUNNING

    def test_start_sets_remaining_time(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            timer.start(25)
            # Immediately after start, remaining should be full duration
            assert timer.get_remaining() == 25 * 60.0

    def test_start_sets_original_duration(self) -> None:
        timer = Timer()
        timer.start(10)
        assert timer.get_original_duration() == 10

    def test_start_from_expired_is_allowed(self) -> None:
        """After expiry the timer can be started again."""
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(1)
            # Jump past the 1-minute duration
            mock_time.monotonic.return_value = 61.0
            # Force state check via get_remaining
            timer.get_remaining()
            assert timer.get_state() == TimerState.EXPIRED
            # Now start again
            mock_time.monotonic.return_value = 100.0
            timer.start(5)
            assert timer.get_state() == TimerState.RUNNING
            assert timer.get_original_duration() == 5

    # --- Invalid durations ---

    def test_start_with_zero_raises_value_error(self) -> None:
        timer = Timer()
        with pytest.raises(ValueError):
            timer.start(0)

    def test_start_with_negative_raises_value_error(self) -> None:
        timer = Timer()
        with pytest.raises(ValueError):
            timer.start(-1)

    def test_start_with_over_60_raises_value_error(self) -> None:
        timer = Timer()
        with pytest.raises(ValueError):
            timer.start(61)

    def test_start_with_non_integer_raises_type_error(self) -> None:
        timer = Timer()
        with pytest.raises(TypeError):
            timer.start(25.5)  # type: ignore[arg-type]

    # --- Invalid state transitions ---

    def test_start_when_running_raises_invalid_state(self) -> None:
        timer = Timer()
        timer.start(25)
        with pytest.raises(InvalidStateError):
            timer.start(10)

    def test_start_when_paused_raises_invalid_state(self) -> None:
        timer = Timer()
        timer.start(25)
        timer.pause()
        with pytest.raises(InvalidStateError):
            timer.start(10)


# ---------------------------------------------------------------------------
# get_remaining()
# ---------------------------------------------------------------------------


class TestTimerGetRemaining:
    """get_remaining() returns remaining seconds, using time.monotonic()."""

    def test_remaining_decreases_over_time(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(25)

            mock_time.monotonic.return_value = 10.0  # 10 seconds later
            assert timer.get_remaining() == pytest.approx(25 * 60.0 - 10.0)

    def test_remaining_never_goes_negative(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(1)  # 60 seconds

            mock_time.monotonic.return_value = 120.0  # well past expiry
            assert timer.get_remaining() == 0.0

    def test_remaining_is_zero_when_idle(self) -> None:
        timer = Timer()
        assert timer.get_remaining() == 0.0


# ---------------------------------------------------------------------------
# pause()
# ---------------------------------------------------------------------------


class TestTimerPause:
    """pause() transitions RUNNING -> PAUSED."""

    def test_pause_transitions_to_paused(self) -> None:
        timer = Timer()
        timer.start(25)
        timer.pause()
        assert timer.get_state() == TimerState.PAUSED

    def test_pause_freezes_remaining_time(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(25)

            mock_time.monotonic.return_value = 10.0
            timer.pause()
            remaining_at_pause = timer.get_remaining()

            # Time passes but remaining must stay frozen
            mock_time.monotonic.return_value = 100.0
            assert timer.get_remaining() == remaining_at_pause

    # --- Invalid state transitions ---

    def test_pause_when_idle_raises_invalid_state(self) -> None:
        timer = Timer()
        with pytest.raises(InvalidStateError):
            timer.pause()

    def test_pause_when_paused_raises_invalid_state(self) -> None:
        timer = Timer()
        timer.start(25)
        timer.pause()
        with pytest.raises(InvalidStateError):
            timer.pause()

    def test_pause_when_expired_raises_invalid_state(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(1)
            mock_time.monotonic.return_value = 61.0
            timer.get_remaining()  # trigger expiration
            with pytest.raises(InvalidStateError):
                timer.pause()


# ---------------------------------------------------------------------------
# resume()
# ---------------------------------------------------------------------------


class TestTimerResume:
    """resume() transitions PAUSED -> RUNNING."""

    def test_resume_transitions_to_running(self) -> None:
        timer = Timer()
        timer.start(25)
        timer.pause()
        timer.resume()
        assert timer.get_state() == TimerState.RUNNING

    def test_resume_continues_countdown(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(25)

            mock_time.monotonic.return_value = 10.0
            timer.pause()
            remaining_at_pause = timer.get_remaining()

            mock_time.monotonic.return_value = 50.0  # 40s pass while paused
            timer.resume()

            mock_time.monotonic.return_value = 55.0  # 5s after resume
            assert timer.get_remaining() == pytest.approx(remaining_at_pause - 5.0)

    # --- Invalid state transitions ---

    def test_resume_when_idle_raises_invalid_state(self) -> None:
        timer = Timer()
        with pytest.raises(InvalidStateError):
            timer.resume()

    def test_resume_when_running_raises_invalid_state(self) -> None:
        timer = Timer()
        timer.start(25)
        with pytest.raises(InvalidStateError):
            timer.resume()

    def test_resume_when_expired_raises_invalid_state(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(1)
            mock_time.monotonic.return_value = 61.0
            timer.get_remaining()  # trigger expiration
            with pytest.raises(InvalidStateError):
                timer.resume()


# ---------------------------------------------------------------------------
# restart()
# ---------------------------------------------------------------------------


class TestTimerRestart:
    """restart() resets to original duration and transitions to RUNNING."""

    def test_restart_from_running(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(10)

            mock_time.monotonic.return_value = 30.0  # 30s elapsed
            timer.restart()
            assert timer.get_state() == TimerState.RUNNING
            assert timer.get_remaining() == pytest.approx(10 * 60.0)

    def test_restart_from_paused(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(10)

            mock_time.monotonic.return_value = 30.0
            timer.pause()
            timer.restart()
            assert timer.get_state() == TimerState.RUNNING
            assert timer.get_remaining() == pytest.approx(10 * 60.0)

    def test_restart_from_expired(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(1)

            mock_time.monotonic.return_value = 61.0
            timer.get_remaining()  # trigger expiration
            assert timer.get_state() == TimerState.EXPIRED

            timer.restart()
            assert timer.get_state() == TimerState.RUNNING
            assert timer.get_remaining() == pytest.approx(1 * 60.0)

    def test_restart_preserves_original_duration(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(15)
            timer.restart()
            assert timer.get_original_duration() == 15

    # --- Invalid state transitions ---

    def test_restart_when_idle_raises_invalid_state(self) -> None:
        timer = Timer()
        with pytest.raises(InvalidStateError):
            timer.restart()


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------


class TestTimerExpiration:
    """Timer automatically transitions to EXPIRED when remaining hits 0."""

    def test_timer_expires_when_time_elapses(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(1)  # 60 seconds

            mock_time.monotonic.return_value = 60.0  # exactly at boundary
            assert timer.get_remaining() == 0.0
            assert timer.get_state() == TimerState.EXPIRED

    def test_expired_timer_remaining_is_zero(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(1)

            mock_time.monotonic.return_value = 120.0
            assert timer.get_remaining() == 0.0

    def test_state_is_expired_after_time_elapses(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(1)

            mock_time.monotonic.return_value = 61.0
            timer.get_remaining()  # trigger check
            assert timer.get_state() == TimerState.EXPIRED


# ---------------------------------------------------------------------------
# get_original_duration()
# ---------------------------------------------------------------------------


class TestTimerOriginalDuration:
    """get_original_duration() returns the configured minutes."""

    def test_returns_zero_when_idle(self) -> None:
        timer = Timer()
        assert timer.get_original_duration() == 0

    def test_returns_duration_after_start(self) -> None:
        timer = Timer()
        timer.start(25)
        assert timer.get_original_duration() == 25

    def test_returns_duration_after_restart(self) -> None:
        timer = Timer()
        with patch("redgreen.core.timer.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            timer.start(25)
            timer.restart()
            assert timer.get_original_duration() == 25
