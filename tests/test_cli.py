"""Tests for the redgreen CLI layer.

Every test mocks ``Session`` so the test suite is fully independent of
the session-manager implementation (which is being developed in parallel).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click.testing
import pytest

from redgreen.cli.main import cli
from redgreen.core.timer import InvalidStateError


@pytest.fixture()
def runner() -> click.testing.CliRunner:
    """Return a Click CliRunner for invoking CLI commands."""
    return click.testing.CliRunner()


# ---------------------------------------------------------------------------
# redgreen start
# ---------------------------------------------------------------------------


class TestStartCommand:
    """Tests for ``redgreen start <minutes>``."""

    @patch("redgreen.cli.main.Session")
    def test_start_success(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.start.return_value = "Session started: 10 minutes"
        result = runner.invoke(cli, ["start", "10"])
        assert result.exit_code == 0
        assert "Session started: 10 minutes" in result.output
        mock_session_cls.return_value.start.assert_called_once_with(10)

    def test_start_missing_argument(self, runner: click.testing.CliRunner) -> None:
        """``redgreen start`` without a minutes argument should fail."""
        result = runner.invoke(cli, ["start"])
        assert result.exit_code != 0

    def test_start_invalid_argument(self, runner: click.testing.CliRunner) -> None:
        """``redgreen start abc`` should fail with a Click type validation error."""
        result = runner.invoke(cli, ["start", "abc"])
        assert result.exit_code != 0

    @patch("redgreen.cli.main.Session")
    def test_start_invalid_state_error(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        """When Session.start raises InvalidStateError, print to stderr and exit 1."""
        mock_session_cls.return_value.start.side_effect = InvalidStateError(
            "start() is not valid from running state"
        )
        result = runner.invoke(cli, ["start", "10"])
        assert result.exit_code == 1
        assert "start() is not valid from running state" in result.output


# ---------------------------------------------------------------------------
# redgreen status
# ---------------------------------------------------------------------------


class TestStatusCommand:
    """Tests for ``redgreen status``."""

    @patch("redgreen.cli.main.Session")
    def test_status_active(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.status.return_value = ("7:34 remaining", 0)
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "7:34 remaining" in result.output

    @patch("redgreen.cli.main.Session")
    def test_status_no_session(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.status.return_value = ("No active session", 1)
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 1
        assert "No active session" in result.output


# ---------------------------------------------------------------------------
# redgreen pause
# ---------------------------------------------------------------------------


class TestPauseCommand:
    """Tests for ``redgreen pause``."""

    @patch("redgreen.cli.main.Session")
    def test_pause_success(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.pause.return_value = "Session paused at 7:34 remaining"
        result = runner.invoke(cli, ["pause"])
        assert result.exit_code == 0
        assert "Session paused at 7:34 remaining" in result.output

    @patch("redgreen.cli.main.Session")
    def test_pause_invalid_state_error(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.pause.side_effect = InvalidStateError(
            "pause() is not valid from idle state"
        )
        result = runner.invoke(cli, ["pause"])
        assert result.exit_code == 1
        assert "pause() is not valid from idle state" in result.output


# ---------------------------------------------------------------------------
# redgreen resume
# ---------------------------------------------------------------------------


class TestResumeCommand:
    """Tests for ``redgreen resume``."""

    @patch("redgreen.cli.main.Session")
    def test_resume_success(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.resume.return_value = "Session resumed: 7:34 remaining"
        result = runner.invoke(cli, ["resume"])
        assert result.exit_code == 0
        assert "Session resumed: 7:34 remaining" in result.output

    @patch("redgreen.cli.main.Session")
    def test_resume_invalid_state_error(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.resume.side_effect = InvalidStateError(
            "resume() is not valid from idle state"
        )
        result = runner.invoke(cli, ["resume"])
        assert result.exit_code == 1
        assert "resume() is not valid from idle state" in result.output


# ---------------------------------------------------------------------------
# redgreen restart
# ---------------------------------------------------------------------------


class TestRestartCommand:
    """Tests for ``redgreen restart``."""

    @patch("redgreen.cli.main.Session")
    def test_restart_success(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.restart.return_value = "Session restarted: 10 minutes"
        result = runner.invoke(cli, ["restart"])
        assert result.exit_code == 0
        assert "Session restarted: 10 minutes" in result.output

    @patch("redgreen.cli.main.Session")
    def test_restart_invalid_state_error(
        self, mock_session_cls: MagicMock, runner: click.testing.CliRunner
    ) -> None:
        mock_session_cls.return_value.restart.side_effect = InvalidStateError(
            "restart() is not valid from idle state"
        )
        result = runner.invoke(cli, ["restart"])
        assert result.exit_code == 1
        assert "restart() is not valid from idle state" in result.output


# ---------------------------------------------------------------------------
# redgreen --version
# ---------------------------------------------------------------------------


class TestVersionFlag:
    """Tests for ``redgreen --version``."""

    def test_version_output(self, runner: click.testing.CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
