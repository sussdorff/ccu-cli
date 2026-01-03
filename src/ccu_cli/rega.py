"""ReGa Script API client for CCU."""

from typing import Any

import httpx

from .config import CCUConfig


class ReGaError(Exception):
    """Error from ReGa script execution."""

    pass


class ReGaClient:
    """Client for CCU ReGa Script API (port 8181).

    Used for operations not available via CCU-Jack, such as
    creating, renaming, and deleting rooms.
    """

    REGA_PORT = 8181

    def __init__(self, config: CCUConfig):
        self.config = config
        self._client: httpx.Client | None = None

    @property
    def base_url(self) -> str:
        """Return the base URL for ReGa API."""
        scheme = "https" if self.config.https else "http"
        return f"{scheme}://{self.config.host}:{self.REGA_PORT}"

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
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

    def create_room(self, name: str) -> int:
        """Create a new room.

        Args:
            name: Name for the new room

        Returns:
            ID of the created room

        Raises:
            ReGaError: If room creation fails
        """
        script = f"""
object room = dom.CreateObject(OT_ROOM);
room.Name("{name}");
WriteLine(room.ID());
"""
        result = self.execute(script)
        # Response format: "<id>\r\n<xml...>"
        # Extract the ID from the first line
        lines = result.strip().split("\n")
        if lines:
            first_line = lines[0].strip()
            try:
                return int(first_line)
            except ValueError:
                raise ReGaError(f"Failed to create room: {result}")
        raise ReGaError(f"No room ID returned: {result}")

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
