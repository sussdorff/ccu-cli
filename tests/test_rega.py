"""Tests for ReGaClient."""

import pytest
import httpx
from httpx import MockTransport, Response

from ccu_cli.config import CCUConfig
from ccu_cli.rega import ReGaClient, RoomDevice


@pytest.fixture
def config() -> CCUConfig:
    """Test configuration."""
    return CCUConfig(host="test-ccu", port=2121)


@pytest.fixture
def mock_rega_client(config):
    """Factory for creating ReGaClient with mocked transport."""

    def factory(handler):
        client = ReGaClient(config)
        client._client = httpx.Client(
            transport=MockTransport(handler),
        )
        return client

    return factory


class TestExecute:
    """Tests for ReGaClient.execute()."""

    def test_posts_script_to_rega_endpoint(self, mock_rega_client):
        """Should POST script to rega.exe endpoint."""
        captured = {}

        def handler(request):
            captured["url"] = str(request.url)
            captured["method"] = request.method
            captured["body"] = request.read().decode("utf-8")
            return Response(200, text="result\n<xml><r><v>ok</v></r></xml>")

        client = mock_rega_client(handler)
        result = client.execute("WriteLine('test');")

        assert captured["method"] == "POST"
        assert "rega.exe" in captured["url"]
        assert "WriteLine" in captured["body"]
        assert result == "result"

    def test_strips_xml_metadata_from_response(self, mock_rega_client):
        """Should remove XML metadata from response."""

        def handler(request):
            return Response(200, text="output line 1\noutput line 2\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        result = client.execute("some script")

        assert result == "output line 1\noutput line 2"
        assert "<xml>" not in result

    def test_handles_response_without_xml(self, mock_rega_client):
        """Should handle response without XML metadata."""

        def handler(request):
            return Response(200, text="plain output")

        client = mock_rega_client(handler)
        result = client.execute("some script")

        assert result == "plain output"


class TestAddDeviceToRoom:
    """Tests for ReGaClient.add_device_to_room()."""

    def test_executes_add_script(self, mock_rega_client):
        """Should execute script to add channel to room."""
        captured = {}

        def handler(request):
            captured["body"] = request.read().decode("utf-8")
            return Response(200, text="OK\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        client.add_device_to_room(1234, 5678)

        assert "dom.GetObject(1234)" in captured["body"]
        assert "dom.GetObject(5678)" in captured["body"]
        assert "room.Add(channel.ID())" in captured["body"]

    def test_raises_on_room_not_found(self, mock_rega_client):
        """Should raise ValueError when room not found."""

        def handler(request):
            return Response(200, text="ERROR:Room not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ValueError, match="Room not found"):
            client.add_device_to_room(9999, 5678)

    def test_raises_on_channel_not_found(self, mock_rega_client):
        """Should raise ValueError when channel not found."""

        def handler(request):
            return Response(200, text="ERROR:Channel not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ValueError, match="Channel not found"):
            client.add_device_to_room(1234, 9999)


class TestRemoveDeviceFromRoom:
    """Tests for ReGaClient.remove_device_from_room()."""

    def test_executes_remove_script(self, mock_rega_client):
        """Should execute script to remove channel from room."""
        captured = {}

        def handler(request):
            captured["body"] = request.read().decode("utf-8")
            return Response(200, text="OK\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)
        client.remove_device_from_room(1234, 5678)

        assert "dom.GetObject(1234)" in captured["body"]
        assert "dom.GetObject(5678)" in captured["body"]
        assert "room.Remove(channel.ID())" in captured["body"]

    def test_raises_on_room_not_found(self, mock_rega_client):
        """Should raise ValueError when room not found."""

        def handler(request):
            return Response(200, text="ERROR:Room not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ValueError, match="Room not found"):
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
        """Should raise ValueError when room not found."""

        def handler(request):
            return Response(200, text="ERROR:Room not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ValueError, match="Room not found"):
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
        """Should raise ValueError when channel not found."""

        def handler(request):
            return Response(200, text="ERROR:Channel not found\n<xml><r><v>x</v></r></xml>")

        client = mock_rega_client(handler)

        with pytest.raises(ValueError, match="Channel not found"):
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

    def test_closes_client_on_exit(self, config):
        """Should close HTTP client when exiting context."""
        client = ReGaClient(config)
        # Force client creation
        client._client = httpx.Client(transport=MockTransport(lambda r: Response(200)))

        with client:
            assert client._client is not None

        assert client._client is None
