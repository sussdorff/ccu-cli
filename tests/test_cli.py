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


@pytest.fixture
def mock_rega_context(mocker):
    """Mock get_rega_client to return a controllable mock."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mocker.patch("ccu_cli.cli.get_rega_client", return_value=mock)
    return mock


class TestRoomListCommand:
    """Tests for 'ccu room list' command."""

    def test_displays_rooms_table(self, runner, mock_rega_context):
        """Should display rooms in a table."""
        mock_rega_context.list_rooms.return_value = [
            {"id": 1234, "name": "Living Room"},
            {"id": 5678, "name": "Kitchen"},
        ]

        result = runner.invoke(main, ["room", "list"])

        assert result.exit_code == 0
        assert "1234" in result.output
        assert "Living Room" in result.output
        assert "5678" in result.output
        assert "Kitchen" in result.output

    def test_handles_empty_room_list(self, runner, mock_rega_context):
        """Should display empty table when no rooms exist."""
        mock_rega_context.list_rooms.return_value = []

        result = runner.invoke(main, ["room", "list"])

        assert result.exit_code == 0
        assert "Rooms" in result.output  # Table title still shown


class TestRoomCreateCommand:
    """Tests for 'ccu room create' command."""

    def test_creates_room(self, runner, mock_rega_context):
        """Should create room and display success message."""
        mock_rega_context.create_room.return_value = 1234

        result = runner.invoke(main, ["room", "create", "Living Room"])

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "Living Room" in result.output
        assert "1234" in result.output
        mock_rega_context.create_room.assert_called_once_with("Living Room")

    def test_handles_error(self, runner, mock_rega_context):
        """Should display error message on failure."""
        from ccu_cli.rega import ReGaError

        mock_rega_context.create_room.side_effect = ReGaError("Script failed")

        result = runner.invoke(main, ["room", "create", "Test Room"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestRoomRenameCommand:
    """Tests for 'ccu room rename' command."""

    def test_renames_room(self, runner, mock_rega_context):
        """Should rename room and display success message."""
        result = runner.invoke(main, ["room", "rename", "1234", "New Name"])

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "New Name" in result.output
        mock_rega_context.rename_room.assert_called_once_with(1234, "New Name")

    def test_handles_room_not_found(self, runner, mock_rega_context):
        """Should display error if room not found."""
        from ccu_cli.rega import ReGaError

        mock_rega_context.rename_room.side_effect = ReGaError("Room not found")

        result = runner.invoke(main, ["room", "rename", "9999", "New Name"])

        assert result.exit_code != 0
        assert "Room not found" in result.output


class TestRoomDeleteCommand:
    """Tests for 'ccu room delete' command."""

    def test_deletes_room_with_confirmation(self, runner, mock_rega_context):
        """Should delete room after confirmation."""
        result = runner.invoke(main, ["room", "delete", "1234"], input="y\n")

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_rega_context.delete_room.assert_called_once_with(1234)

    def test_cancels_without_confirmation(self, runner, mock_rega_context):
        """Should not delete room if confirmation declined."""
        result = runner.invoke(main, ["room", "delete", "1234"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_rega_context.delete_room.assert_not_called()

    def test_deletes_with_yes_flag(self, runner, mock_rega_context):
        """Should delete room without confirmation if --yes flag used."""
        result = runner.invoke(main, ["room", "delete", "--yes", "1234"])

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_rega_context.delete_room.assert_called_once_with(1234)

    def test_handles_room_not_found(self, runner, mock_rega_context):
        """Should display error if room not found."""
        from ccu_cli.rega import ReGaError

        mock_rega_context.delete_room.side_effect = ReGaError("Room not found")

        result = runner.invoke(main, ["room", "delete", "--yes", "9999"])

        assert result.exit_code != 0
        assert "Room not found" in result.output
