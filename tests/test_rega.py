"""Tests for ReGaClient."""

import pytest
from httpx import Response

from ccu_cli.rega import ReGaClient, ReGaError
from ccu_cli.config import CCUConfig


@pytest.fixture
def rega_config() -> CCUConfig:
    """Test configuration for ReGa client."""
    return CCUConfig(host="test-ccu", port=2121)


@pytest.fixture
def mock_rega_client(rega_config, mock_transport_factory):
    """Factory for creating ReGaClient with mocked transport."""
    import httpx

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
