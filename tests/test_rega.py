"""Tests for ReGaClient."""

import pytest
import httpx
from httpx import MockTransport, Response

from ccu_cli.config import CCUConfig
from ccu_cli.rega import Program, ReGaClient, ReGaError, RoomDevice


@pytest.fixture
def rega_config() -> CCUConfig:
    """Test configuration for ReGa client."""
    return CCUConfig(host="test-ccu", port=2121)


@pytest.fixture
def mock_rega_client(rega_config, mock_transport_factory):
    """Factory for creating ReGaClient with mocked transport."""

    def factory(handler):
        client = ReGaClient(rega_config)
        client._client = httpx.Client(
            base_url=client.base_url,
            transport=mock_transport_factory(handler),
        )
        return client

    return factory


class TestReGaClientInit:
    """Tests for ReGaClient initialization."""

    def test_uses_port_8181(self, rega_config):
        """Should use ReGa port 8181, not CCU-Jack port."""
        client = ReGaClient(rega_config)
        assert ":8181" in client.base_url

    def test_uses_http_by_default(self, rega_config):
        """Should use HTTP by default."""
        client = ReGaClient(rega_config)
        assert client.base_url.startswith("http://")

    def test_uses_https_when_configured(self):
        """Should use HTTPS when configured."""
        config = CCUConfig(host="test-ccu", https=True)
        client = ReGaClient(config)
        assert client.base_url.startswith("https://")


class TestExecute:
    """Tests for ReGaClient.execute()."""

    def test_posts_script_to_rega_exe(self, mock_rega_client):
        """Should POST script to /rega.exe endpoint."""
        captured_request = {}

        def handler(request):
            captured_request["method"] = request.method
            captured_request["path"] = str(request.url.path)
            captured_request["body"] = request.read().decode()
            captured_request["content_type"] = request.headers.get("content-type")
            return Response(200, text="output")

        client = mock_rega_client(handler)
        client.execute("WriteLine('test');")

        assert captured_request["method"] == "POST"
        assert captured_request["path"] == "/rega.exe"
        assert "WriteLine" in captured_request["body"]
        assert captured_request["content_type"] == "text/plain"

    def test_returns_response_text(self, mock_rega_client):
        """Should return the response text."""

        def handler(request):
            return Response(200, text="Hello World\r\n<xml>...")

        client = mock_rega_client(handler)
        result = client.execute("WriteLine('Hello World');")

        assert "Hello World" in result


class TestCreateRoom:
    """Tests for ReGaClient.create_room()."""

    def test_creates_room_and_returns_id(self, mock_rega_client):
        """Should create room and return its ID."""

        def handler(request):
            body = request.read().decode()
            assert 'room.Name("Living Room")' in body
            return Response(200, text="1234\r\n<xml>...</xml>")

        client = mock_rega_client(handler)
        room_id = client.create_room("Living Room")

        assert room_id == 1234

    def test_handles_multiline_response(self, mock_rega_client):
        """Should extract ID from first line of response."""

        def handler(request):
            return Response(200, text="5678\n<xml>additional data</xml>")

        client = mock_rega_client(handler)
        room_id = client.create_room("Kitchen")

        assert room_id == 5678

    def test_raises_error_on_invalid_response(self, mock_rega_client):
        """Should raise ReGaError if ID cannot be parsed."""

        def handler(request):
            return Response(200, text="ERROR: Script failed")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Failed to create room"):
            client.create_room("Test Room")


class TestRenameRoom:
    """Tests for ReGaClient.rename_room()."""

    def test_renames_room(self, mock_rega_client):
        """Should send rename script with room ID and new name."""
        captured_body = {}

        def handler(request):
            captured_body["script"] = request.read().decode()
            return Response(200, text="OK\r\n<xml>...</xml>")

        client = mock_rega_client(handler)
        client.rename_room(1234, "New Name")

        assert "dom.GetObject(1234)" in captured_body["script"]
        assert 'room.Name("New Name")' in captured_body["script"]

    def test_raises_error_if_room_not_found(self, mock_rega_client):
        """Should raise ReGaError if room does not exist."""

        def handler(request):
            return Response(200, text="ERROR:Room not found\r\n<xml>...")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Room not found"):
            client.rename_room(9999, "New Name")


class TestDeleteRoom:
    """Tests for ReGaClient.delete_room()."""

    def test_deletes_room(self, mock_rega_client):
        """Should send delete script with room ID."""
        captured_body = {}

        def handler(request):
            captured_body["script"] = request.read().decode()
            return Response(200, text="OK\r\n<xml>...</xml>")

        client = mock_rega_client(handler)
        client.delete_room(1234)

        assert "dom.GetObject(1234)" in captured_body["script"]
        assert "dom.DeleteObject" in captured_body["script"]

    def test_raises_error_if_room_not_found(self, mock_rega_client):
        """Should raise ReGaError if room does not exist."""

        def handler(request):
            return Response(200, text="ERROR:Room not found\r\n<xml>...")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Room not found"):
            client.delete_room(9999)


class TestListRooms:
    """Tests for ReGaClient.list_rooms()."""

    def test_returns_room_list(self, mock_rega_client):
        """Should parse semicolon-separated room list."""

        def handler(request):
            return Response(200, text="1234;Living Room\n5678;Kitchen\n<xml>...")

        client = mock_rega_client(handler)
        rooms = client.list_rooms()

        assert len(rooms) == 2
        assert {"id": 1234, "name": "Living Room"} in rooms
        assert {"id": 5678, "name": "Kitchen"} in rooms

    def test_handles_empty_room_list(self, mock_rega_client):
        """Should return empty list when no rooms exist."""

        def handler(request):
            return Response(200, text="<xml>...</xml>")

        client = mock_rega_client(handler)
        rooms = client.list_rooms()

        assert rooms == []

    def test_handles_room_with_semicolon_in_name(self, mock_rega_client):
        """Should handle room names containing semicolons."""

        def handler(request):
            return Response(200, text="1234;Room; With; Semicolons\n")

        client = mock_rega_client(handler)
        rooms = client.list_rooms()

        assert len(rooms) == 1
        assert rooms[0]["id"] == 1234
        assert rooms[0]["name"] == "Room; With; Semicolons"


class TestAddDeviceToRoom:
    """Tests for ReGaClient.add_device_to_room()."""

    def test_executes_add_script(self, mock_rega_client):
        """Should execute script to add channel to room."""
        captured = {}

        def handler(request):
            captured["body"] = request.read().decode()
            return Response(200, text="OK\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        client.add_device_to_room(1234, 5678)

        assert "dom.GetObject(1234)" in captured["body"]
        assert "dom.GetObject(5678)" in captured["body"]
        assert "room.Add(channel.ID())" in captured["body"]

    def test_raises_on_room_not_found(self, mock_rega_client):
        """Should raise ReGaError when room not found."""

        def handler(request):
            return Response(200, text="ERROR:Room not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Room not found"):
            client.add_device_to_room(9999, 5678)

    def test_raises_on_channel_not_found(self, mock_rega_client):
        """Should raise ReGaError when channel not found."""

        def handler(request):
            return Response(200, text="ERROR:Channel not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Channel not found"):
            client.add_device_to_room(1234, 9999)


class TestRemoveDeviceFromRoom:
    """Tests for ReGaClient.remove_device_from_room()."""

    def test_executes_remove_script(self, mock_rega_client):
        """Should execute script to remove channel from room."""
        captured = {}

        def handler(request):
            captured["body"] = request.read().decode()
            return Response(200, text="OK\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        client.remove_device_from_room(1234, 5678)

        assert "dom.GetObject(1234)" in captured["body"]
        assert "dom.GetObject(5678)" in captured["body"]
        assert "room.Remove(channel.ID())" in captured["body"]

    def test_raises_on_room_not_found(self, mock_rega_client):
        """Should raise ReGaError when room not found."""

        def handler(request):
            return Response(200, text="ERROR:Room not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Room not found"):
            client.remove_device_from_room(9999, 5678)


class TestListRoomDevices:
    """Tests for ReGaClient.list_room_devices()."""

    def test_parses_device_list(self, mock_rega_client):
        """Should parse semicolon-separated device output."""

        def handler(request):
            output = "1001;Living Room Light;ABC123:1\n1002;Living Room Switch;DEF456:2\n"
            return Response(200, text=output + "<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        devices = client.list_room_devices(1234)

        assert len(devices) == 2
        assert devices[0] == RoomDevice(id=1001, name="Living Room Light", address="ABC123:1")
        assert devices[1] == RoomDevice(id=1002, name="Living Room Switch", address="DEF456:2")

    def test_returns_empty_list_for_empty_room(self, mock_rega_client):
        """Should return empty list when room has no devices."""

        def handler(request):
            return Response(200, text="\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        devices = client.list_room_devices(1234)

        assert devices == []

    def test_raises_on_room_not_found(self, mock_rega_client):
        """Should raise ReGaError when room not found."""

        def handler(request):
            return Response(200, text="ERROR:Room not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Room not found"):
            client.list_room_devices(9999)

    def test_skips_malformed_lines(self, mock_rega_client):
        """Should skip lines that don't have expected format."""

        def handler(request):
            output = "1001;Living Room Light;ABC123:1\nmalformed line\n1002;Switch;DEF456:2\n"
            return Response(200, text=output + "<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        devices = client.list_room_devices(1234)

        assert len(devices) == 2


class TestGetDeviceRoom:
    """Tests for ReGaClient.get_device_room()."""

    def test_returns_room_id(self, mock_rega_client):
        """Should return room ID when channel is in a room."""

        def handler(request):
            return Response(200, text="1234\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        room_id = client.get_device_room(5678)

        assert room_id == 1234

    def test_returns_none_when_not_in_room(self, mock_rega_client):
        """Should return None when channel is not in any room."""

        def handler(request):
            return Response(200, text="\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        room_id = client.get_device_room(5678)

        assert room_id is None

    def test_raises_on_channel_not_found(self, mock_rega_client):
        """Should raise ReGaError when channel not found."""

        def handler(request):
            return Response(200, text="ERROR:Channel not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Channel not found"):
            client.get_device_room(9999)

    def test_returns_first_room_for_multi_room_channel(self, mock_rega_client):
        """Should return first room ID when channel is in multiple rooms."""

        def handler(request):
            return Response(200, text="1234\n5678\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        room_id = client.get_device_room(9999)

        assert room_id == 1234


class TestReGaClientContextManager:
    """Tests for ReGaClient context manager."""

    def test_closes_client_on_exit(self, rega_config):
        """Should close HTTP client when exiting context."""
        client = ReGaClient(rega_config)
        # Force client creation
        client._client = httpx.Client(transport=MockTransport(lambda r: Response(200)))

        with client:
            assert client._client is not None

        assert client._client is None


class TestListPrograms:
    """Tests for ReGaClient.list_programs()."""

    def test_returns_program_list(self, mock_rega_client):
        """Should parse semicolon-separated program list."""

        def handler(request):
            return Response(
                200,
                text="1001;All Lights Off;Turn off all lights;true;true;1704067200\n1002;Morning Routine;;false;true;0\n<xml>...",
            )

        client = mock_rega_client(handler)
        programs = client.list_programs()

        assert len(programs) == 2
        assert programs[0] == Program(
            id=1001,
            name="All Lights Off",
            description="Turn off all lights",
            active=True,
            visible=True,
            last_execute_time=1704067200,
        )
        assert programs[1] == Program(
            id=1002,
            name="Morning Routine",
            description="",
            active=False,
            visible=True,
            last_execute_time=0,
        )

    def test_handles_empty_program_list(self, mock_rega_client):
        """Should return empty list when no programs exist."""

        def handler(request):
            return Response(200, text="<xml>...</xml>")

        client = mock_rega_client(handler)
        programs = client.list_programs()

        assert programs == []


class TestGetProgram:
    """Tests for ReGaClient.get_program()."""

    def test_returns_program_by_id(self, mock_rega_client):
        """Should return program details when found."""

        def handler(request):
            return Response(
                200,
                text="1001;All Lights Off;Turn off all lights;true;true;1704067200\n<xml>...",
            )

        client = mock_rega_client(handler)
        program = client.get_program(1001)

        assert program is not None
        assert program.id == 1001
        assert program.name == "All Lights Off"
        assert program.description == "Turn off all lights"
        assert program.active is True

    def test_returns_none_when_not_found(self, mock_rega_client):
        """Should return None when program not found."""

        def handler(request):
            return Response(200, text="ERROR:Program not found\n<xml>...")

        client = mock_rega_client(handler)
        program = client.get_program(9999)

        assert program is None


class TestGetProgramByName:
    """Tests for ReGaClient.get_program_by_name()."""

    def test_returns_program_by_name(self, mock_rega_client):
        """Should return program details when found by name."""

        def handler(request):
            body = request.read().decode()
            assert 'Get("All Lights Off")' in body
            return Response(
                200,
                text="1001;All Lights Off;Turn off all lights;true;true;1704067200\n<xml>...",
            )

        client = mock_rega_client(handler)
        program = client.get_program_by_name("All Lights Off")

        assert program is not None
        assert program.name == "All Lights Off"

    def test_returns_none_when_not_found(self, mock_rega_client):
        """Should return None when program not found by name."""

        def handler(request):
            return Response(200, text="ERROR:Program not found\n<xml>...")

        client = mock_rega_client(handler)
        program = client.get_program_by_name("NonExistent")

        assert program is None


class TestRunProgram:
    """Tests for ReGaClient.run_program()."""

    def test_executes_program(self, mock_rega_client):
        """Should execute program by ID."""
        captured = {}

        def handler(request):
            captured["body"] = request.read().decode()
            return Response(200, text="OK\n<xml>...</xml>")

        client = mock_rega_client(handler)
        client.run_program(1001)

        assert "dom.GetObject(1001)" in captured["body"]
        assert "ProgramExecute()" in captured["body"]

    def test_raises_on_not_found(self, mock_rega_client):
        """Should raise ReGaError when program not found."""

        def handler(request):
            return Response(200, text="ERROR:Program not found\n<xml>...")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Program not found"):
            client.run_program(9999)


class TestDeleteProgram:
    """Tests for ReGaClient.delete_program()."""

    def test_deletes_program(self, mock_rega_client):
        """Should delete program by ID."""
        captured = {}

        def handler(request):
            captured["body"] = request.read().decode()
            return Response(200, text="OK\n<xml>...</xml>")

        client = mock_rega_client(handler)
        client.delete_program(1001)

        assert "dom.GetObject(1001)" in captured["body"]
        assert "dom.DeleteObject" in captured["body"]

    def test_raises_on_not_found(self, mock_rega_client):
        """Should raise ReGaError when program not found."""

        def handler(request):
            return Response(200, text="ERROR:Program not found\n<xml>...")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Program not found"):
            client.delete_program(9999)


class TestSetProgramActive:
    """Tests for ReGaClient.set_program_active()."""

    def test_enables_program(self, mock_rega_client):
        """Should enable program."""
        captured = {}

        def handler(request):
            captured["body"] = request.read().decode()
            return Response(200, text="OK\n<xml>...</xml>")

        client = mock_rega_client(handler)
        client.set_program_active(1001, True)

        assert "dom.GetObject(1001)" in captured["body"]
        assert "Active(true)" in captured["body"]

    def test_disables_program(self, mock_rega_client):
        """Should disable program."""
        captured = {}

        def handler(request):
            captured["body"] = request.read().decode()
            return Response(200, text="OK\n<xml>...</xml>")

        client = mock_rega_client(handler)
        client.set_program_active(1001, False)

        assert "dom.GetObject(1001)" in captured["body"]
        assert "Active(false)" in captured["body"]

    def test_raises_on_not_found(self, mock_rega_client):
        """Should raise ReGaError when program not found."""

        def handler(request):
            return Response(200, text="ERROR:Program not found\n<xml>...")

        client = mock_rega_client(handler)

        with pytest.raises(ReGaError, match="Program not found"):
            client.set_program_active(9999, True)
