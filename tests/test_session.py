"""Comprehensive tests for the Session Manager."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from redgreen.core.session import Session
from redgreen.core.timer import InvalidStateError

# ---------------------------------------------------------------------------
# Helper: read the persisted JSON state file
# ---------------------------------------------------------------------------


def _read_state(config_dir: Path) -> dict:
    """Read and return the session.json content as a dict."""
    return json.loads((config_dir / "session.json").read_text())


# ---------------------------------------------------------------------------
# Time formatting
# ---------------------------------------------------------------------------


class TestTimeFormatting:
    """Session formats remaining time as M:SS."""

    def test_format_seven_minutes_thirty_four_seconds(self, tmp_path: Path) -> None:
        """7 minutes 34 seconds -> '7:34'."""
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            # Advance so remaining = 454 seconds = 7m 34s
            mock_time.monotonic.return_value = 146.0
            msg, code = session.status()
            assert msg == "7:34 remaining"

    def test_format_five_seconds(self, tmp_path: Path) -> None:
        """5 seconds -> '0:05'."""
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(1)  # 60 seconds

            # Advance so remaining = 5 seconds
            mock_time.monotonic.return_value = 55.0
            msg, code = session.status()
            assert msg == "0:05 remaining"

    def test_format_twelve_minutes_exactly(self, tmp_path: Path) -> None:
        """12 minutes 0 seconds -> '12:00'."""
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(12)

            # Immediately, remaining = 720 seconds = 12:00
            msg, code = session.status()
            assert msg == "12:00 remaining"


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------


class TestSessionStart:
    """Session.start() creates a new timed session."""

    def test_start_returns_message(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            result = session.start(10)
            assert result == "Session started: 10 minutes"

    def test_start_when_already_running_raises(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(10)
            with pytest.raises(InvalidStateError):
                session.start(5)

    def test_start_when_paused_raises(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(10)
            session.pause()
            with pytest.raises(InvalidStateError):
                session.start(5)


# ---------------------------------------------------------------------------
# status()
# ---------------------------------------------------------------------------


class TestSessionStatus:
    """Session.status() returns (message, exit_code)."""

    def test_running_status(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            mock_time.monotonic.return_value = 146.0  # 454s left = 7:34
            msg, code = session.status()
            assert msg == "7:34 remaining"
            assert code == 0

    def test_paused_status(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            mock_time.monotonic.return_value = 146.0
            session.pause()

            msg, code = session.status()
            assert msg == "7:34 remaining (paused)"
            assert code == 0

    def test_no_session_status(self, tmp_path: Path) -> None:
        session = Session(config_dir=tmp_path)
        msg, code = session.status()
        assert msg == "No active session"
        assert code == 1

    def test_expired_status(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(1)

            mock_time.monotonic.return_value = 61.0  # past 60s
            msg, code = session.status()
            assert msg == "Session expired"
            assert code == 1


# ---------------------------------------------------------------------------
# pause()
# ---------------------------------------------------------------------------


class TestSessionPause:
    """Session.pause() pauses a running session."""

    def test_pause_returns_message(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            mock_time.monotonic.return_value = 146.0
            result = session.pause()
            assert result == "Session paused at 7:34 remaining"


# ---------------------------------------------------------------------------
# resume()
# ---------------------------------------------------------------------------


class TestSessionResume:
    """Session.resume() resumes a paused session."""

    def test_resume_returns_message(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            mock_time.monotonic.return_value = 146.0
            session.pause()

            mock_time.monotonic.return_value = 200.0  # time passes while paused
            result = session.resume()
            assert result == "Session resumed: 7:34 remaining"


# ---------------------------------------------------------------------------
# restart()
# ---------------------------------------------------------------------------


class TestSessionRestart:
    """Session.restart() restarts with original duration."""

    def test_restart_returns_message(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            mock_time.monotonic.return_value = 300.0
            result = session.restart()
            assert result == "Session restarted: 10 minutes"


# ---------------------------------------------------------------------------
# Persistence — state file written after mutations
# ---------------------------------------------------------------------------


class TestSessionPersistence:
    """Session persists state to session.json after every mutation."""

    def test_start_persists_state(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_706_745_600.0
            session = Session(config_dir=tmp_path)
            session.start(10)

        state = _read_state(tmp_path)
        assert state["state"] == "running"
        assert state["duration_minutes"] == 10
        assert state["remaining_seconds"] == 600.0
        assert state["started_at"] == 1_706_745_600.0

    def test_pause_persists_state(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_706_745_600.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            mock_time.monotonic.return_value = 146.0
            mock_time.time.return_value = 1_706_745_746.0
            session.pause()

        state = _read_state(tmp_path)
        assert state["state"] == "paused"
        assert state["remaining_seconds"] == pytest.approx(454.0)

    def test_resume_persists_state(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_706_745_600.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            mock_time.monotonic.return_value = 146.0
            mock_time.time.return_value = 1_706_745_746.0
            session.pause()

            mock_time.monotonic.return_value = 200.0
            mock_time.time.return_value = 1_706_745_800.0
            session.resume()

        state = _read_state(tmp_path)
        assert state["state"] == "running"
        assert state["remaining_seconds"] == pytest.approx(454.0)
        assert state["started_at"] == 1_706_745_800.0

    def test_restart_persists_state(self, tmp_path: Path) -> None:
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_706_745_600.0
            session = Session(config_dir=tmp_path)
            session.start(10)

            mock_time.monotonic.return_value = 300.0
            mock_time.time.return_value = 1_706_745_900.0
            session.restart()

        state = _read_state(tmp_path)
        assert state["state"] == "running"
        assert state["duration_minutes"] == 10
        assert state["remaining_seconds"] == 600.0
        assert state["started_at"] == 1_706_745_900.0


# ---------------------------------------------------------------------------
# Loading from disk — restore state across processes
# ---------------------------------------------------------------------------


class TestSessionLoadFromDisk:
    """Session constructor loads state from existing session.json."""

    def test_load_running_session(self, tmp_path: Path) -> None:
        """A running session is restored, accounting for elapsed wall time."""
        state = {
            "state": "running",
            "duration_minutes": 10,
            "remaining_seconds": 600.0,
            "started_at": 1_000_000.0,
        }
        (tmp_path / "session.json").write_text(json.dumps(state))

        with patch("redgreen.core.session.time") as mock_time:
            # Wall clock says 100s have passed since started_at
            mock_time.time.return_value = 1_000_100.0
            mock_time.monotonic.return_value = 5000.0
            session = Session(config_dir=tmp_path)

            msg, code = session.status()
            assert code == 0
            assert msg == "8:20 remaining"  # 600 - 100 = 500s = 8:20

    def test_load_paused_session(self, tmp_path: Path) -> None:
        """A paused session is restored with frozen remaining time."""
        state = {
            "state": "paused",
            "duration_minutes": 10,
            "remaining_seconds": 454.0,
            "started_at": 1_000_000.0,
        }
        (tmp_path / "session.json").write_text(json.dumps(state))

        with patch("redgreen.core.session.time") as mock_time:
            mock_time.time.return_value = 1_500_000.0  # much later — doesn't matter
            mock_time.monotonic.return_value = 5000.0
            session = Session(config_dir=tmp_path)

        msg, code = session.status()
        assert code == 0
        assert msg == "7:34 remaining (paused)"

    def test_load_expired_session_from_disk(self, tmp_path: Path) -> None:
        """If elapsed wall time > remaining, session is expired."""
        state = {
            "state": "running",
            "duration_minutes": 10,
            "remaining_seconds": 60.0,
            "started_at": 1_000_000.0,
        }
        (tmp_path / "session.json").write_text(json.dumps(state))

        with patch("redgreen.core.session.time") as mock_time:
            # 120s have passed but only 60s were remaining -> expired
            mock_time.time.return_value = 1_000_120.0
            mock_time.monotonic.return_value = 5000.0
            session = Session(config_dir=tmp_path)

        msg, code = session.status()
        assert msg == "Session expired"
        assert code == 1

    def test_load_with_no_state_file(self, tmp_path: Path) -> None:
        """No state file means no active session."""
        session = Session(config_dir=tmp_path)
        msg, code = session.status()
        assert msg == "No active session"
        assert code == 1


# ---------------------------------------------------------------------------
# Config directory creation
# ---------------------------------------------------------------------------


class TestConfigDirectory:
    """Session creates the config directory if it does not exist."""

    def test_creates_missing_config_dir(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "nested" / "config" / "dir"
        assert not config_dir.exists()

        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session(config_dir=config_dir)
            session.start(5)

        assert config_dir.exists()
        assert (config_dir / "session.json").exists()

    def test_default_config_dir(self) -> None:
        """When no config_dir is given, defaults to ~/.config/redgreen/."""
        with patch("redgreen.core.session.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            mock_time.time.return_value = 1_000_000.0
            session = Session()
        assert session._config_dir == Path.home() / ".config" / "redgreen"
