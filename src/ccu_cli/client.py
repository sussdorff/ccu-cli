"""CCU-Jack API client."""

from typing import Any

import httpx

from .config import CCUConfig


class CCUClient:
    """Client for CCU-Jack REST API (VEAP protocol)."""

    def __init__(self, config: CCUConfig):
        self.config = config
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                auth=self.config.auth,
                timeout=30.0,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "CCUClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _get(self, path: str) -> Any:
        """Perform GET request and return JSON response."""
        response = self.client.get(path)
        response.raise_for_status()
        return response.json()

    def _put(self, path: str, data: Any) -> Any:
        """Perform PUT request with JSON data."""
        response = self.client.put(path, json=data)
        response.raise_for_status()
        return response.json() if response.content else None

    def get_vendor_info(self) -> dict[str, Any]:
        """Get CCU-Jack vendor information."""
        return self._get("/~vendor")

    def list_devices(self) -> list[dict[str, Any]]:
        """List all devices."""
        data = self._get("/device/~pv")
        return data.get("links", [])

    def get_device(self, serial: str) -> dict[str, Any]:
        """Get device details including channels."""
        return self._get(f"/device/{serial}/~pv")

    def get_datapoint(self, serial: str, channel: int, datapoint: str) -> Any:
        """Read a datapoint value."""
        data = self._get(f"/device/{serial}/{channel}/{datapoint}/~pv")
        return data.get("v")

    def set_datapoint(self, serial: str, channel: int, datapoint: str, value: Any) -> None:
        """Set a datapoint value."""
        self._put(f"/device/{serial}/{channel}/{datapoint}/~pv", {"v": value})

    def get_device_config(self, serial: str, channel: int) -> dict[str, Any]:
        """Get device/channel configuration (MASTER parameters)."""
        return self._get(f"/device/{serial}/{channel}/$MASTER/~pv")

    def set_device_config(self, serial: str, channel: int, params: dict[str, Any]) -> None:
        """Set device/channel configuration parameters."""
        self._put(f"/device/{serial}/{channel}/$MASTER/~pv", params)

    def list_sysvars(self) -> list[dict[str, Any]]:
        """List all system variables."""
        data = self._get("/sysvar/~pv")
        return data.get("links", [])

    def get_sysvar(self, name: str) -> Any:
        """Get a system variable value."""
        data = self._get(f"/sysvar/{name}/~pv")
        return data.get("v")

    def set_sysvar(self, name: str, value: Any) -> None:
        """Set a system variable value."""
        self._put(f"/sysvar/{name}/~pv", {"v": value})

    def list_programs(self) -> list[dict[str, Any]]:
        """List all programs."""
        data = self._get("/program/~pv")
        return data.get("links", [])

    def run_program(self, name: str) -> None:
        """Execute a program."""
        self._put(f"/program/{name}/~pv", {"v": True})
