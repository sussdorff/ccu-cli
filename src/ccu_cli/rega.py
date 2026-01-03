"""ReGa Script API client for HomeMatic CCU."""

from dataclasses import dataclass

import httpx

from .config import CCUConfig


@dataclass
class RoomDevice:
    """Device/channel in a room."""

    id: int
    name: str
    address: str


class ReGaClient:
    """Client for ReGa Script API on HomeMatic CCU.

    The ReGa (logic layer) provides access to rooms, functions, and
    device assignments that aren't available through CCU-Jack's VEAP API.
    """

    def __init__(self, config: CCUConfig):
        self.config = config
        self._client: httpx.Client | None = None

    @property
    def rega_url(self) -> str:
        """Return the ReGa Script endpoint URL."""
        scheme = "https" if self.config.https else "http"
        return f"{scheme}://{self.config.host}:8181/rega.exe"

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                auth=self.config.auth,
                timeout=30.0,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ReGaClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def execute(self, script: str) -> str:
        """Execute a ReGa script and return the output.

        Args:
            script: HomeMatic Script code to execute

        Returns:
            Script output (text before the XML metadata)

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        response = self.client.post(
            self.rega_url,
            content=script,
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        response.raise_for_status()

        # ReGa returns output followed by XML metadata
        # Split on <xml> to get just the script output
        text = response.text
        if "<xml>" in text:
            text = text.split("<xml>")[0]
        return text.strip()

    def add_device_to_room(self, room_id: int, channel_id: int) -> None:
        """Add a device/channel to a room.

        Args:
            room_id: The room's internal ID
            channel_id: The channel's internal ID
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
        if result.startswith("ERROR:"):
            raise ValueError(result[6:])

    def remove_device_from_room(self, room_id: int, channel_id: int) -> None:
        """Remove a device/channel from a room.

        Args:
            room_id: The room's internal ID
            channel_id: The channel's internal ID
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
        if result.startswith("ERROR:"):
            raise ValueError(result[6:])

    def list_room_devices(self, room_id: int) -> list[RoomDevice]:
        """List all devices/channels in a room.

        Args:
            room_id: The room's internal ID

        Returns:
            List of devices in the room
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
        if result.startswith("ERROR:"):
            raise ValueError(result[6:])

        devices = []
        for line in result.splitlines():
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
        if result.startswith("ERROR:"):
            raise ValueError(result[6:])

        # Return the first room ID found (a channel could be in multiple rooms)
        for line in result.splitlines():
            line = line.strip()
            if line:
                return int(line)
        return None
