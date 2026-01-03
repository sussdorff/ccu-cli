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


@pytest.fixture
def mock_rega_context(mocker):
    """Mock get_rega_client to return a controllable mock."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mocker.patch("ccu_cli.cli.get_rega_client", return_value=mock)
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


class TestProgramListCommand:
    """Tests for 'ccu program list' command."""

    def test_displays_programs_table(self, runner, mock_rega_context):
        """Should display programs in a table."""
        from ccu_cli.rega import Program

        mock_rega_context.list_programs.return_value = [
            Program(id=9001, name="All Lights Off", description="", active=True, visible=True, last_execute_time=0),
        ]

        result = runner.invoke(main, ["program", "list"])

        assert result.exit_code == 0
        assert "All Lights Off" in result.output
        assert "9001" in result.output


class TestProgramShowCommand:
    """Tests for 'ccu program show' command."""

    def test_displays_program_details(self, runner, mock_rega_context):
        """Should display program details."""
        from ccu_cli.rega import Program

        mock_rega_context.get_program.return_value = Program(
            id=9001, name="All Lights Off", description="Turn off all lights", active=True, visible=True, last_execute_time=1704067200
        )

        result = runner.invoke(main, ["program", "show", "9001"])

        assert result.exit_code == 0
        assert "All Lights Off" in result.output
        assert "Turn off all lights" in result.output
        assert "Yes" in result.output  # Active

    def test_resolves_by_name(self, runner, mock_rega_context):
        """Should resolve program by name."""
        from ccu_cli.rega import Program

        mock_rega_context.get_program.return_value = None  # ID lookup fails
        mock_rega_context.get_program_by_name.return_value = Program(
            id=9001, name="AllLightsOff", description="", active=True, visible=True, last_execute_time=0
        )

        result = runner.invoke(main, ["program", "show", "AllLightsOff"])

        assert result.exit_code == 0
        assert "AllLightsOff" in result.output


class TestProgramRunCommand:
    """Tests for 'ccu program run' command."""

    def test_executes_program(self, runner, mock_rega_context):
        """Should execute the program."""
        from ccu_cli.rega import Program

        mock_rega_context.get_program.return_value = Program(
            id=9001, name="AllLightsOff", description="", active=True, visible=True, last_execute_time=0
        )

        result = runner.invoke(main, ["program", "run", "9001"])

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_rega_context.run_program.assert_called_once_with(9001)


class TestProgramDeleteCommand:
    """Tests for 'ccu program delete' command."""

    def test_deletes_program_with_confirmation(self, runner, mock_rega_context):
        """Should delete program after confirmation."""
        from ccu_cli.rega import Program

        mock_rega_context.get_program.return_value = Program(
            id=9001, name="Test Program", description="", active=True, visible=True, last_execute_time=0
        )

        result = runner.invoke(main, ["program", "delete", "9001"], input="y\n")

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_rega_context.delete_program.assert_called_once_with(9001)

    def test_cancels_without_confirmation(self, runner, mock_rega_context):
        """Should not delete program if confirmation declined."""
        from ccu_cli.rega import Program

        mock_rega_context.get_program.return_value = Program(
            id=9001, name="Test Program", description="", active=True, visible=True, last_execute_time=0
        )

        result = runner.invoke(main, ["program", "delete", "9001"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_rega_context.delete_program.assert_not_called()

    def test_deletes_with_yes_flag(self, runner, mock_rega_context):
        """Should delete program without confirmation if --yes flag used."""
        from ccu_cli.rega import Program

        mock_rega_context.get_program.return_value = Program(
            id=9001, name="Test Program", description="", active=True, visible=True, last_execute_time=0
        )

        result = runner.invoke(main, ["program", "delete", "--yes", "9001"])

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_rega_context.delete_program.assert_called_once_with(9001)


class TestProgramEnableCommand:
    """Tests for 'ccu program enable' command."""

    def test_enables_program(self, runner, mock_rega_context):
        """Should enable the program."""
        from ccu_cli.rega import Program

        mock_rega_context.get_program.return_value = Program(
            id=9001, name="Test Program", description="", active=False, visible=True, last_execute_time=0
        )

        result = runner.invoke(main, ["program", "enable", "9001"])

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "enabled" in result.output
        mock_rega_context.set_program_active.assert_called_once_with(9001, True)


class TestProgramDisableCommand:
    """Tests for 'ccu program disable' command."""

    def test_disables_program(self, runner, mock_rega_context):
        """Should disable the program."""
        from ccu_cli.rega import Program

        mock_rega_context.get_program.return_value = Program(
            id=9001, name="Test Program", description="", active=True, visible=True, last_execute_time=0
        )

        result = runner.invoke(main, ["program", "disable", "9001"])

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "disabled" in result.output
        mock_rega_context.set_program_active.assert_called_once_with(9001, False)


class TestRoomsCommand:
    """Tests for 'ccu rooms' command (via CCU-Jack)."""

    def test_displays_rooms_table(self, runner, mock_client_context):
        """Should display rooms in a table."""
        mock_client_context.list_rooms.return_value = [
            {"rel": "room", "href": "1234", "title": "Living Room"},
            {"rel": "room", "href": "5678", "title": "Kitchen"},
        ]

        result = runner.invoke(main, ["rooms"])

        assert result.exit_code == 0
        assert "1234" in result.output
        assert "Living Room" in result.output
        assert "5678" in result.output
        assert "Kitchen" in result.output

    def test_handles_empty_room_list(self, runner, mock_client_context):
        """Should display empty table when no rooms exist."""
        mock_client_context.list_rooms.return_value = []

        result = runner.invoke(main, ["rooms"])

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
