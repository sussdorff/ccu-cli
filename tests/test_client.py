"""Tests for CCUClient."""

import pytest
from httpx import Response


class TestListDevices:
    """Tests for CCUClient.list_devices()."""

    def test_returns_device_links(self, mock_client, devices_response):
        """Should return list of device links from response."""

        def handler(request):
            assert request.url.path == "/device"
            return Response(200, json=devices_response)

        client = mock_client(handler)
        devices = client.list_devices()

        assert len(devices) == 3
        device_hrefs = [d["href"] for d in devices if d.get("rel") == "device"]
        assert "NEQ0123456" in device_hrefs
        assert "NEQ0789012" in device_hrefs

    def test_handles_empty_response(self, mock_client):
        """Should handle empty device list."""

        def handler(request):
            return Response(200, json={"~links": []})

        client = mock_client(handler)
        devices = client.list_devices()

        assert devices == []


class TestGetDatapoint:
    """Tests for CCUClient.get_datapoint()."""

    def test_reads_datapoint_value(self, mock_client):
        """Should extract value from ~pv response."""

        def handler(request):
            assert request.url.path == "/device/NEQ123/1/TEMPERATURE/~pv"
            return Response(200, json={"v": 21.5, "ts": 1234567890})

        client = mock_client(handler)
        value = client.get_datapoint("NEQ123", 1, "TEMPERATURE")

        assert value == 21.5

    def test_reads_boolean_datapoint(self, mock_client):
        """Should handle boolean values."""

        def handler(request):
            return Response(200, json={"v": True, "ts": 1234567890})

        client = mock_client(handler)
        value = client.get_datapoint("NEQ123", 1, "STATE")

        assert value is True


class TestSetDatapoint:
    """Tests for CCUClient.set_datapoint()."""

    def test_sends_put_with_value(self, mock_client):
        """Should PUT the value wrapped in {v: ...}."""
        captured_request = {}

        def handler(request):
            captured_request["method"] = request.method
            captured_request["path"] = str(request.url.path)
            captured_request["body"] = request.read()
            return Response(200)

        client = mock_client(handler)
        client.set_datapoint("NEQ123", 1, "STATE", True)

        assert captured_request["method"] == "PUT"
        assert captured_request["path"] == "/device/NEQ123/1/STATE/~pv"
        assert b'"v": true' in captured_request["body"] or b'"v":true' in captured_request["body"]


class TestListSysvars:
    """Tests for CCUClient.list_sysvars()."""

    def test_returns_sysvar_links(self, mock_client, sysvars_response):
        """Should return list of system variable links."""

        def handler(request):
            assert request.url.path == "/sysvar"
            return Response(200, json=sysvars_response)

        client = mock_client(handler)
        sysvars = client.list_sysvars()

        assert len(sysvars) == 3
        sysvar_titles = [s["title"] for s in sysvars if s.get("rel") == "sysvar"]
        assert "Presence" in sysvar_titles
        assert "AlarmActive" in sysvar_titles


class TestListPrograms:
    """Tests for CCUClient.list_programs()."""

    def test_returns_program_links(self, mock_client, programs_response):
        """Should return list of program links."""

        def handler(request):
            assert request.url.path == "/program"
            return Response(200, json=programs_response)

        client = mock_client(handler)
        programs = client.list_programs()

        assert len(programs) == 3
        program_titles = [p["title"] for p in programs if p.get("rel") == "program"]
        assert "All Lights Off" in program_titles
        assert "Good Night" in program_titles


class TestListRooms:
    """Tests for CCUClient.list_rooms()."""

    def test_returns_room_links(self, mock_client, rooms_response):
        """Should return list of room links from response."""

        def handler(request):
            assert request.url.path == "/room"
            return Response(200, json=rooms_response)

        client = mock_client(handler)
        rooms = client.list_rooms()

        assert len(rooms) == 3
        room_titles = [r["title"] for r in rooms if r.get("rel") == "room"]
        assert "Living Room" in room_titles
        assert "Kitchen" in room_titles

    def test_handles_empty_response(self, mock_client):
        """Should handle empty room list."""

        def handler(request):
            return Response(200, json={"~links": []})

        client = mock_client(handler)
        rooms = client.list_rooms()

        assert rooms == []


class TestGetRoom:
    """Tests for CCUClient.get_room()."""

    def test_gets_room_by_id(self, mock_client, room_detail_response):
        """Should fetch room details by ID."""

        def handler(request):
            assert request.url.path == "/room/1234"
            return Response(200, json=room_detail_response)

        client = mock_client(handler)
        room = client.get_room("1234")

        assert room["identifier"] == "1234"
        assert room["title"] == "Living Room"

    def test_gets_room_by_name(self, mock_client, rooms_response, room_detail_response):
        """Should lookup room by name and fetch details."""
        call_count = {"value": 0}

        def handler(request):
            call_count["value"] += 1
            if request.url.path == "/room/Living%20Room":
                # First call with name fails (room names are not valid paths)
                return Response(404)
            elif request.url.path == "/room":
                return Response(200, json=rooms_response)
            elif request.url.path == "/room/1234":
                return Response(200, json=room_detail_response)
            return Response(404)

        client = mock_client(handler)
        room = client.get_room("Living Room")

        assert room["identifier"] == "1234"
        assert room["title"] == "Living Room"

    def test_raises_for_unknown_room(self, mock_client, rooms_response):
        """Should raise ValueError for unknown room name."""

        def handler(request):
            if request.url.path == "/room/Unknown%20Room":
                return Response(404)
            elif request.url.path == "/room":
                return Response(200, json=rooms_response)
            return Response(404)

        client = mock_client(handler)

        with pytest.raises(ValueError, match="Room not found: Unknown Room"):
            client.get_room("Unknown Room")
