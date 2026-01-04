"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock

from ccu_cli.cli import main
from ccu_cli.backend import Channel, DataPoint, Device, Program as BackendProgram, SysVar


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_backend_context(mocker):
    """Mock get_backend to return a controllable mock."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mocker.patch("ccu_cli.cli.get_backend", return_value=mock)
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

    def test_displays_devices_table(self, runner, mock_backend_context):
        """Should display devices in a table."""
        mock_backend_context.list_devices.return_value = [
            Device(address="NEQ123", name="Living Room", model="HmIP-PSM", device_type="switch", interface="HmIP-RF", firmware="1.0.0", available=True),
            Device(address="NEQ456", name="Kitchen", model="HmIP-eTRV", device_type="thermostat", interface="HmIP-RF", firmware="1.0.0", available=True),
        ]

        result = runner.invoke(main, ["devices"])

        assert result.exit_code == 0
        assert "NEQ123" in result.output
        assert "Living Room" in result.output
        assert "NEQ456" in result.output
        assert "Kitchen" in result.output

    def test_shows_availability_status(self, runner, mock_backend_context):
        """Should show availability status."""
        mock_backend_context.list_devices.return_value = [
            Device(address="NEQ123", name="Switch", model="HmIP-PSM", device_type="switch", interface="HmIP-RF", firmware="1.0.0", available=True),
            Device(address="NEQ456", name="Offline", model="HmIP-PSM", device_type="switch", interface="HmIP-RF", firmware="1.0.0", available=False),
        ]

        result = runner.invoke(main, ["devices"])

        assert result.exit_code == 0
        assert "✓" in result.output  # Available device
        assert "✗" in result.output  # Unavailable device


class TestGetCommand:
    """Tests for 'ccu get' command."""

    def test_reads_and_displays_value(self, runner, mock_backend_context):
        """Should display the datapoint value."""
        mock_backend_context.read_value.return_value = 21.5

        result = runner.invoke(main, ["get", "NEQ123:1/TEMPERATURE"])

        assert result.exit_code == 0
        assert "21.5" in result.output
        mock_backend_context.read_value.assert_called_once_with("NEQ123:1", "TEMPERATURE")

    def test_rejects_invalid_path_format(self, runner, mock_backend_context):
        """Should fail with invalid path format."""
        result = runner.invoke(main, ["get", "invalid-path"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestSetCommand:
    """Tests for 'ccu set' command."""

    def test_sets_boolean_true(self, runner, mock_backend_context):
        """Should parse and set boolean true."""
        result = runner.invoke(main, ["set", "NEQ123:1/STATE", "true"])

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_backend_context.write_value.assert_called_once_with("NEQ123:1", "STATE", True)

    def test_sets_numeric_value(self, runner, mock_backend_context):
        """Should parse and set numeric values."""
        result = runner.invoke(main, ["set", "NEQ123:1/LEVEL", "75"])

        assert result.exit_code == 0
        mock_backend_context.write_value.assert_called_once_with("NEQ123:1", "LEVEL", 75)

    def test_sets_float_value(self, runner, mock_backend_context):
        """Should parse and set float values."""
        result = runner.invoke(main, ["set", "NEQ123:1/SETPOINT", "21.5"])

        assert result.exit_code == 0
        mock_backend_context.write_value.assert_called_once_with("NEQ123:1", "SETPOINT", 21.5)


class TestSysvarsCommand:
    """Tests for 'ccu sysvars' command."""

    def test_displays_sysvars_table(self, runner, mock_backend_context):
        """Should display system variables in a table."""
        mock_backend_context.list_sysvars.return_value = [
            SysVar(name="Presence", value=True, data_type="BOOL", unit=None),
            SysVar(name="Temperature", value=21.5, data_type="FLOAT", unit="°C"),
        ]

        result = runner.invoke(main, ["sysvars"])

        assert result.exit_code == 0
        assert "Presence" in result.output
        assert "Temperature" in result.output


class TestProgramListCommand:
    """Tests for 'ccu program list' command."""

    def test_displays_programs_table(self, runner, mock_backend_context):
        """Should display programs in a table."""
        mock_backend_context.list_programs.return_value = [
            BackendProgram(pid="9001", name="All Lights Off", is_active=True, is_internal=False, last_execute_time=None),
        ]

        result = runner.invoke(main, ["program", "list"])

        assert result.exit_code == 0
        assert "All Lights Off" in result.output
        assert "9001" in result.output

    def test_skips_internal_programs(self, runner, mock_backend_context):
        """Should skip internal programs by default."""
        mock_backend_context.list_programs.return_value = [
            BackendProgram(pid="9001", name="User Program", is_active=True, is_internal=False, last_execute_time=None),
            BackendProgram(pid="9002", name="Internal Program", is_active=True, is_internal=True, last_execute_time=None),
        ]

        result = runner.invoke(main, ["program", "list"])

        assert result.exit_code == 0
        assert "User Program" in result.output
        assert "Internal Program" not in result.output


class TestProgramGetCommand:
    """Tests for 'ccu program get' command."""

    def test_displays_program_details(self, runner, mock_backend_context):
        """Should display program details."""
        mock_backend_context.get_program.return_value = BackendProgram(
            pid="9001", name="All Lights Off", is_active=True, is_internal=False, last_execute_time=None
        )

        result = runner.invoke(main, ["program", "get", "9001"])

        assert result.exit_code == 0
        assert "All Lights Off" in result.output
        assert "Yes" in result.output  # Active

    def test_handles_program_not_found(self, runner, mock_backend_context):
        """Should show error if program not found."""
        mock_backend_context.get_program.return_value = None

        result = runner.invoke(main, ["program", "get", "nonexistent"])

        assert result.exit_code != 0
        assert "Program not found" in result.output


class TestProgramRunCommand:
    """Tests for 'ccu program run' command."""

    def test_executes_program(self, runner, mock_backend_context):
        """Should execute the program."""
        mock_backend_context.get_program.return_value = BackendProgram(
            pid="9001", name="AllLightsOff", is_active=True, is_internal=False, last_execute_time=None
        )

        result = runner.invoke(main, ["program", "run", "9001"])

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_backend_context.run_program.assert_called_once_with("9001")


class TestProgramDeleteCommand:
    """Tests for 'ccu program delete' command."""

    def test_deletes_program_with_confirmation(self, runner, mock_backend_context):
        """Should delete program after confirmation."""
        mock_backend_context.get_program.return_value = BackendProgram(
            pid="9001", name="Test Program", is_active=True, is_internal=False, last_execute_time=None
        )
        mock_backend_context.delete_program.return_value = "Test Program"

        result = runner.invoke(main, ["program", "delete", "9001"], input="y\n")

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_backend_context.delete_program.assert_called_once_with("9001")

    def test_cancels_without_confirmation(self, runner, mock_backend_context):
        """Should not delete program if confirmation declined."""
        mock_backend_context.get_program.return_value = BackendProgram(
            pid="9001", name="Test Program", is_active=True, is_internal=False, last_execute_time=None
        )

        result = runner.invoke(main, ["program", "delete", "9001"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_backend_context.delete_program.assert_not_called()

    def test_deletes_with_yes_flag(self, runner, mock_backend_context):
        """Should delete program without confirmation if --yes flag used."""
        mock_backend_context.get_program.return_value = BackendProgram(
            pid="9001", name="Test Program", is_active=True, is_internal=False, last_execute_time=None
        )
        mock_backend_context.delete_program.return_value = "Test Program"

        result = runner.invoke(main, ["program", "delete", "--yes", "9001"])

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_backend_context.delete_program.assert_called_once_with("9001")


class TestProgramEnableCommand:
    """Tests for 'ccu program enable' command."""

    def test_enables_program(self, runner, mock_backend_context):
        """Should enable the program."""
        mock_backend_context.get_program.return_value = BackendProgram(
            pid="9001", name="Test Program", is_active=False, is_internal=False, last_execute_time=None
        )

        result = runner.invoke(main, ["program", "enable", "9001"])

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "enabled" in result.output
        mock_backend_context.set_program_active.assert_called_once_with("9001", True)


class TestProgramDisableCommand:
    """Tests for 'ccu program disable' command."""

    def test_disables_program(self, runner, mock_backend_context):
        """Should disable the program."""
        mock_backend_context.get_program.return_value = BackendProgram(
            pid="9001", name="Test Program", is_active=True, is_internal=False, last_execute_time=None
        )

        result = runner.invoke(main, ["program", "disable", "9001"])

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "disabled" in result.output
        mock_backend_context.set_program_active.assert_called_once_with("9001", False)


class TestRoomsCommand:
    """Tests for 'ccu rooms' command (via ReGa)."""

    def test_displays_rooms_table(self, runner, mock_rega_context):
        """Should display rooms in a table."""
        mock_rega_context.list_rooms.return_value = [
            {"id": 1234, "name": "Living Room"},
            {"id": 5678, "name": "Kitchen"},
        ]

        result = runner.invoke(main, ["rooms"])

        assert result.exit_code == 0
        assert "1234" in result.output
        assert "Living Room" in result.output
        assert "5678" in result.output
        assert "Kitchen" in result.output

    def test_handles_empty_room_list(self, runner, mock_rega_context):
        """Should display empty table when no rooms exist."""
        mock_rega_context.list_rooms.return_value = []

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


class TestLinkListCommand:
    """Tests for 'ccu link list' command."""

    def test_displays_links_table(self, runner, mock_backend_context):
        """Should display links in a table."""
        from ccu_cli.xmlrpc import DeviceLink

        mock_backend_context.list_links.return_value = [
            DeviceLink(
                sender="000B5D89B014D8:1",
                receiver="0013A40997105E:4",
                name="Test Link",
                description="Test Description",
            ),
        ]

        result = runner.invoke(main, ["link", "list"])

        assert result.exit_code == 0
        assert "000B5D89B014D8:1" in result.output
        assert "0013A40997105E:4" in result.output
        assert "Test Link" in result.output

    def test_shows_no_links_message(self, runner, mock_backend_context):
        """Should display message when no links exist."""
        mock_backend_context.list_links.return_value = []

        result = runner.invoke(main, ["link", "list"])

        assert result.exit_code == 0
        assert "No links found" in result.output

    def test_filters_by_address(self, runner, mock_backend_context):
        """Should filter links by address."""
        mock_backend_context.list_links.return_value = []

        result = runner.invoke(main, ["link", "list", "-a", "000B5D89B014D8:1"])

        assert result.exit_code == 0
        mock_backend_context.list_links.assert_called_once_with("000B5D89B014D8:1", "HmIP-RF")


class TestLinkGetCommand:
    """Tests for 'ccu link get' command."""

    def test_displays_link_details(self, runner, mock_backend_context):
        """Should display link details."""
        from ccu_cli.xmlrpc import LinkInfo

        mock_backend_context.get_link.return_value = LinkInfo(
            sender="000B5D89B014D8:1",
            receiver="0013A40997105E:4",
            name="Test Link",
            description="Test Description",
            flags=1,
        )

        result = runner.invoke(
            main, ["link", "get", "000B5D89B014D8:1", "0013A40997105E:4"]
        )

        assert result.exit_code == 0
        assert "000B5D89B014D8:1" in result.output
        assert "Test Link" in result.output

    def test_shows_not_found_error(self, runner, mock_backend_context):
        """Should display error when link not found."""
        mock_backend_context.get_link.return_value = None

        result = runner.invoke(main, ["link", "get", "sender", "receiver"])

        assert result.exit_code != 0
        assert "Link not found" in result.output


class TestLinkCreateCommand:
    """Tests for 'ccu link create' command."""

    def test_creates_link(self, runner, mock_backend_context):
        """Should create a device link."""
        result = runner.invoke(
            main,
            ["link", "create", "000B5D89B014D8:1", "0013A40997105E:4"],
        )

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "Created link" in result.output
        mock_backend_context.create_link.assert_called_once_with(
            "000B5D89B014D8:1", "0013A40997105E:4", "", ""
        )

    def test_creates_link_with_name(self, runner, mock_backend_context):
        """Should create link with name and description."""
        result = runner.invoke(
            main,
            [
                "link",
                "create",
                "000B5D89B014D8:1",
                "0013A40997105E:4",
                "--name",
                "Test Link",
                "--description",
                "Test Desc",
            ],
        )

        assert result.exit_code == 0
        mock_backend_context.create_link.assert_called_once_with(
            "000B5D89B014D8:1", "0013A40997105E:4", "Test Link", "Test Desc"
        )


class TestLinkDeleteCommand:
    """Tests for 'ccu link delete' command."""

    def test_deletes_link_with_confirmation(self, runner, mock_backend_context):
        """Should delete link after confirmation."""
        result = runner.invoke(
            main,
            ["link", "delete", "000B5D89B014D8:1", "0013A40997105E:4"],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_backend_context.delete_link.assert_called_once_with(
            "000B5D89B014D8:1", "0013A40997105E:4"
        )

    def test_cancels_without_confirmation(self, runner, mock_backend_context):
        """Should not delete link if confirmation declined."""
        result = runner.invoke(
            main,
            ["link", "delete", "000B5D89B014D8:1", "0013A40997105E:4"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_backend_context.delete_link.assert_not_called()

    def test_deletes_with_yes_flag(self, runner, mock_backend_context):
        """Should delete link without confirmation if --yes flag used."""
        result = runner.invoke(
            main,
            ["link", "delete", "--yes", "000B5D89B014D8:1", "0013A40997105E:4"],
        )

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_backend_context.delete_link.assert_called_once()


class TestLinkConfigGetCommand:
    """Tests for 'ccu link config get' command."""

    def test_displays_link_params(self, runner, mock_backend_context):
        """Should display link parameters as JSON."""
        mock_backend_context.get_link_paramset.return_value = {
            "LONG_PRESS_TIME": 0.5,
            "DBL_PRESS_TIME": 0.3,
        }

        result = runner.invoke(
            main,
            ["link", "config", "get", "000B5D89B014D8:1", "0013A40997105E:4"],
        )

        assert result.exit_code == 0
        assert "LONG_PRESS_TIME" in result.output
        assert "0.5" in result.output


class TestLinkConfigSetCommand:
    """Tests for 'ccu link config set' command."""

    def test_sets_link_params(self, runner, mock_backend_context):
        """Should set link parameters."""
        result = runner.invoke(
            main,
            [
                "link",
                "config",
                "set",
                "000B5D89B014D8:1",
                "0013A40997105E:4",
                "LONG_PRESS_TIME=1.0",
            ],
        )

        assert result.exit_code == 0
        assert "OK" in result.output
        mock_backend_context.set_link_paramset.assert_called_once_with(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
            {"LONG_PRESS_TIME": 1.0},
            "receiver",
            "HmIP-RF",
        )

    def test_sets_multiple_params(self, runner, mock_backend_context):
        """Should set multiple parameters at once."""
        result = runner.invoke(
            main,
            [
                "link",
                "config",
                "set",
                "sender",
                "receiver",
                "PARAM1=10",
                "PARAM2=true",
                "PARAM3=text",
            ],
        )

        assert result.exit_code == 0
        mock_backend_context.set_link_paramset.assert_called_once_with(
            "sender",
            "receiver",
            {"PARAM1": 10, "PARAM2": True, "PARAM3": "text"},
            "receiver",
            "HmIP-RF",
        )

    def test_sets_params_on_sender_side(self, runner, mock_backend_context):
        """Should set parameters on sender side when --side sender specified."""
        result = runner.invoke(
            main,
            [
                "link",
                "config",
                "set",
                "--side",
                "sender",
                "000B5D89B014D8:1",
                "0013A40997105E:4",
                "LONG_PRESS_TIME=0.5",
            ],
        )

        assert result.exit_code == 0
        mock_backend_context.set_link_paramset.assert_called_once_with(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
            {"LONG_PRESS_TIME": 0.5},
            "sender",
            "HmIP-RF",
        )

    def test_rejects_invalid_format(self, runner, mock_backend_context):
        """Should reject parameters without = sign."""
        result = runner.invoke(
            main,
            [
                "link",
                "config",
                "set",
                "sender",
                "receiver",
                "invalid_param",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid parameter format" in result.output
