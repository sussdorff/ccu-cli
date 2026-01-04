"""ReGa Script API client for CCU."""

from dataclasses import dataclass
from typing import Any

import httpx

from .config import CCUConfig


class ReGaError(Exception):
    """Error from ReGa script execution."""

    pass


@dataclass
class RoomDevice:
    """Device/channel in a room."""

    id: int
    name: str
    address: str


@dataclass
class Program:
    """CCU program details."""

    id: int
    name: str
    description: str
    active: bool
    visible: bool
    last_execute_time: int  # Unix timestamp


class ReGaClient:
    """Client for CCU ReGa Script API (port 8181).

    Used for operations not available via aiohomematic, such as
    creating, renaming, and deleting rooms.
    """

    REGA_PORT = 8181

    def __init__(self, config: CCUConfig):
        self.config = config
        self._client: httpx.Client | None = None

    @property
    def base_url(self) -> str:
        """Return the base URL for ReGa API.

        Note: ReGa API always uses HTTP on port 8181, regardless of main CCU HTTPS setting.
        """
        return f"http://{self.config.host}:{self.REGA_PORT}"

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                auth=self.config.auth,
                timeout=30.0,
                verify=False,  # Allow self-signed certs
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ReGaClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def execute(self, script: str) -> str:
        """Execute a ReGa script and return the response.

        Args:
            script: HomeMatic Script code to execute

        Returns:
            Script output (stdout from WriteLine calls)

        Raises:
            ReGaError: If script execution fails
        """
        response = self.client.post(
            "/rega.exe",
            content=script,
            headers={"Content-Type": "text/plain"},
        )
        response.raise_for_status()
        return response.text

    def rename_room(self, room_id: int, new_name: str) -> None:
        """Rename an existing room.

        Args:
            room_id: ID of the room to rename
            new_name: New name for the room

        Raises:
            ReGaError: If room does not exist or rename fails
        """
        script = f"""
object room = dom.GetObject({room_id});
if (room) {{
  room.Name("{new_name}");
  WriteLine("OK");
}} else {{
  WriteLine("ERROR:Room not found");
}}
"""
        result = self.execute(script)
        first_line = result.strip().split("\n")[0].strip()
        if first_line.startswith("ERROR:"):
            raise ReGaError(first_line[6:])

    def delete_room(self, room_id: int) -> None:
        """Delete a room.

        Args:
            room_id: ID of the room to delete

        Raises:
            ReGaError: If room does not exist or deletion fails
        """
        script = f"""
object room = dom.GetObject({room_id});
if (room) {{
  dom.DeleteObject(room.ID());
  WriteLine("OK");
}} else {{
  WriteLine("ERROR:Room not found");
}}
"""
        result = self.execute(script)
        first_line = result.strip().split("\n")[0].strip()
        if first_line.startswith("ERROR:"):
            raise ReGaError(first_line[6:])

    def list_rooms(self) -> list[dict[str, Any]]:
        """List all rooms.

        Returns:
            List of room dicts with 'id' and 'name' keys
        """
        script = """
string roomId;
foreach(roomId, dom.GetObject(ID_ROOMS).EnumUsedIDs()) {
  object room = dom.GetObject(roomId);
  WriteLine(room.ID() # ";" # room.Name());
}
"""
        result = self.execute(script)
        rooms = []
        for line in result.strip().split("\n"):
            line = line.strip()
            if ";" in line:
                parts = line.split(";", 1)
                try:
                    room_id = int(parts[0])
                    name = parts[1] if len(parts) > 1 else ""
                    rooms.append({"id": room_id, "name": name})
                except ValueError:
                    continue
        return rooms

    def rename_channel(self, channel_id: int, new_name: str) -> None:
        """Rename a channel/device.

        Args:
            channel_id: The channel's internal ID
            new_name: New name for the channel

        Raises:
            ReGaError: If channel not found
        """
        script = f"""
object channel = dom.GetObject({channel_id});
if (channel) {{
    channel.Name("{new_name}");
    WriteLine("OK");
}} else {{
    WriteLine("ERROR:Channel not found");
}}
"""
        result = self.execute(script)
        first_line = result.strip().split("\n")[0].strip()
        if first_line.startswith("ERROR:"):
            raise ReGaError(first_line[6:])

    def add_device_to_room(self, room_id: int, channel_id: int) -> None:
        """Add a device/channel to a room.

        Args:
            room_id: The room's internal ID
            channel_id: The channel's internal ID

        Raises:
            ReGaError: If room or channel not found
        """
        script = f"""
object room = dom.GetObject({room_id});
object channel = dom.GetObject({channel_id});
if (room && channel) {{
    room.Add(channel.ID());
    WriteLine("OK");
}} else {{
    if (!room) {{ WriteLine("ERROR:Room not found"); }}
    if (!channel) {{ WriteLine("ERROR:Channel not found"); }}
}}
"""
        result = self.execute(script)
        first_line = result.strip().split("\n")[0].strip()
        if first_line.startswith("ERROR:"):
            raise ReGaError(first_line[6:])

    def remove_device_from_room(self, room_id: int, channel_id: int) -> None:
        """Remove a device/channel from a room.

        Args:
            room_id: The room's internal ID
            channel_id: The channel's internal ID

        Raises:
            ReGaError: If room or channel not found
        """
        script = f"""
object room = dom.GetObject({room_id});
object channel = dom.GetObject({channel_id});
if (room && channel) {{
    room.Remove(channel.ID());
    WriteLine("OK");
}} else {{
    if (!room) {{ WriteLine("ERROR:Room not found"); }}
    if (!channel) {{ WriteLine("ERROR:Channel not found"); }}
}}
"""
        result = self.execute(script)
        first_line = result.strip().split("\n")[0].strip()
        if first_line.startswith("ERROR:"):
            raise ReGaError(first_line[6:])

    def list_room_devices(self, room_id: int) -> list[RoomDevice]:
        """List all devices/channels in a room.

        Args:
            room_id: The room's internal ID

        Returns:
            List of devices in the room

        Raises:
            ReGaError: If room not found
        """
        script = f"""
object room = dom.GetObject({room_id});
if (room) {{
    string chId;
    foreach(chId, room.EnumUsedIDs()) {{
        object ch = dom.GetObject(chId);
        if (ch) {{
            WriteLine(ch.ID() # ";" # ch.Name() # ";" # ch.Address());
        }}
    }}
}} else {{
    WriteLine("ERROR:Room not found");
}}
"""
        result = self.execute(script)
        first_line = result.strip().split("\n")[0].strip() if result.strip() else ""
        if first_line.startswith("ERROR:"):
            raise ReGaError(first_line[6:])

        devices = []
        for line in result.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(";")
            if len(parts) >= 3:
                devices.append(
                    RoomDevice(
                        id=int(parts[0]),
                        name=parts[1],
                        address=parts[2],
                    )
                )
        return devices

    def get_device_room(self, channel_id: int) -> int | None:
        """Get the room ID for a device/channel.

        Args:
            channel_id: The channel's internal ID

        Returns:
            Room ID if the channel is assigned to a room, None otherwise

        Raises:
            ReGaError: If channel not found
        """
        script = f"""
object channel = dom.GetObject({channel_id});
if (channel) {{
    string roomId;
    foreach(roomId, channel.Rooms().EnumUsedIDs()) {{
        WriteLine(roomId);
    }}
}} else {{
    WriteLine("ERROR:Channel not found");
}}
"""
        result = self.execute(script)
        first_line = result.strip().split("\n")[0].strip() if result.strip() else ""
        if first_line.startswith("ERROR:"):
            raise ReGaError(first_line[6:])

        # Return the first room ID found (a channel could be in multiple rooms)
        for line in result.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("ERROR:"):
                try:
                    return int(line)
                except ValueError:
                    continue
        return None

    # Program operations
    # Note: Most program operations (list, get, run, set_active) are handled
    # by aiohomematic via CCUBackend. Only delete_program is kept here since
    # aiohomematic doesn't support program deletion.

    def delete_program(self, program_id: int) -> None:
        """Delete a program.

        Args:
            program_id: The program's internal ID

        Raises:
            ReGaError: If program not found or deletion fails
        """
        script = f"""
object oProgram = dom.GetObject({program_id});
if (oProgram && oProgram.IsTypeOf(OT_PROGRAM)) {{
    dom.DeleteObject(oProgram.ID());
    WriteLine("OK");
}} else {{
    WriteLine("ERROR:Program not found");
}}
"""
        result = self.execute(script)
        first_line = result.strip().split("\n")[0].strip()
        if first_line.startswith("ERROR:"):
            raise ReGaError(first_line[6:])
