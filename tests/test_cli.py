"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock

from ccu_cli.cli import main


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_client_context(mocker):
    """Mock get_client to return a controllable mock."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mocker.patch("ccu_cli.cli.get_client", return_value=mock)
    return mock


class TestDevicesCommand:
    """Tests for 'ccu devices' command."""

    def test_displays_devices_table(self, runner, mock_client_context):
        """Should display devices in a table."""
        mock_client_context.list_devices.return_value = [
            {"rel": "device", "href": "NEQ123", "title": "Living Room"},
            {"rel": "device", "href": "NEQ456", "title": "Kitchen"},
        ]

        result = runner.invoke(main, ["devices"])

        assert result.exit_code == 0
        assert "NEQ123" in result.output
        assert "Living Room" in result.output
        assert "NEQ456" in result.output
        assert "Kitchen" in result.output

    def test_filters_non_device_links(self, runner, mock_client_context):
        """Should not display non-device links like 'root'."""
        mock_client_context.list_devices.return_value = [
            {"rel": "root", "href": "..", "title": "Root"},
            {"rel": "device", "href": "NEQ123", "title": "Switch"},
        ]

        result = runner.invoke(main, ["devices"])

        assert result.exit_code == 0
        assert "NEQ123" in result.output
        assert "Root" not in result.output


class TestGetCommand:
    """Tests for 'ccu get' command."""

    def test_reads_and_displays_value(self, runner, mock_client_context):
        """Should display the datapoint value."""
        mock_client_context.get_datapoint.return_value = 21.5

        result = runner.invoke(main, ["get", "NEQ123/1/TEMPERATURE"])

        assert result.exit_code == 0
        assert "21.5" in result.output
        mock_client_context.get_datapoint.assert_called_once_with("NEQ123", 1, "TEMPERATURE")

    def test_rejects_invalid_path_format(self, runner, mock_client_context):
        """Should fail with invalid path format."""
        result = runner.invoke(main, ["get", "invalid-path"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestSetCommand:
    """Tests for 'ccu set' command."""

    def test_sets_boolean_true(self, runner, mock_client_context):
        """Should parse and set boolean true."""
        result = runner.invoke(main, ["set", "NEQ123/1/STATE", "true"])

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_client_context.set_datapoint.assert_called_once_with("NEQ123", 1, "STATE", True)

    def test_sets_numeric_value(self, runner, mock_client_context):
        """Should parse and set numeric values."""
        result = runner.invoke(main, ["set", "NEQ123/1/LEVEL", "75"])

        assert result.exit_code == 0
        mock_client_context.set_datapoint.assert_called_once_with("NEQ123", 1, "LEVEL", 75)

    def test_sets_float_value(self, runner, mock_client_context):
        """Should parse and set float values."""
        result = runner.invoke(main, ["set", "NEQ123/1/SETPOINT", "21.5"])

        assert result.exit_code == 0
        mock_client_context.set_datapoint.assert_called_once_with("NEQ123", 1, "SETPOINT", 21.5)


class TestSysvarsCommand:
    """Tests for 'ccu sysvars' command."""

    def test_displays_sysvars_table(self, runner, mock_client_context):
        """Should display system variables in a table."""
        mock_client_context.list_sysvars.return_value = [
            {"rel": "sysvar", "href": "1234", "title": "Presence"},
            {"rel": "sysvar", "href": "5678", "title": "AlarmActive"},
        ]

        result = runner.invoke(main, ["sysvars"])

        assert result.exit_code == 0
        assert "Presence" in result.output
        assert "AlarmActive" in result.output


class TestProgramsCommand:
    """Tests for 'ccu programs' command."""

    def test_displays_programs_table(self, runner, mock_client_context):
        """Should display programs in a table."""
        mock_client_context.list_programs.return_value = [
            {"rel": "program", "href": "9001", "title": "All Lights Off"},
        ]

        result = runner.invoke(main, ["programs"])

        assert result.exit_code == 0
        assert "All Lights Off" in result.output


class TestRunCommand:
    """Tests for 'ccu run' command."""

    def test_executes_program(self, runner, mock_client_context):
        """Should execute the named program."""
        result = runner.invoke(main, ["run", "AllLightsOff"])

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_client_context.run_program.assert_called_once_with("AllLightsOff")
