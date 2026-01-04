"""XML-RPC API client for CCU.

Used for managing Direktverknüpfungen (direct device links).

Ports:
- 2001: BidCos-RF (legacy HomeMatic devices)
- 2010: HmIP-RF (HomeMatic IP devices)
"""

from dataclasses import dataclass
from typing import Any
from xmlrpc.client import ServerProxy

from .config import CCUConfig


class XMLRPCError(Exception):
    """Error from XML-RPC API call."""

    pass


@dataclass
class DeviceLink:
    """A direct device link (Direktverknüpfung)."""

    sender: str  # Sender address (e.g., "000B5D89B014D8:1")
    receiver: str  # Receiver address (e.g., "000E9569A23B4C:4")
    name: str  # Link name
    description: str  # Link description


@dataclass
class LinkInfo:
    """Detailed information about a device link."""

    sender: str
    receiver: str
    name: str
    description: str
    flags: int
    # Additional paramset values can be added as needed


class XMLRPCClient:
    """Client for CCU XML-RPC API.

    Provides access to device linking operations.

    Supports two interfaces:
    - BidCos-RF (port 2001): For legacy HomeMatic devices
    - HmIP-RF (port 2010): For HomeMatic IP devices
    """

    PORT_BIDCOS_RF = 2001
    PORT_HMIP_RF = 2010

    def __init__(self, config: CCUConfig, interface: str = "HmIP-RF"):
        """Initialize XML-RPC client.

        Args:
            config: CCU configuration
            interface: Interface to use ("BidCos-RF" or "HmIP-RF")
        """
        self.config = config
        self.interface = interface
        self._proxy: ServerProxy | None = None

    @property
    def port(self) -> int:
        """Return the port for the current interface."""
        if self.interface == "BidCos-RF":
            return self.PORT_BIDCOS_RF
        return self.PORT_HMIP_RF

    @property
    def base_url(self) -> str:
        """Return the base URL for XML-RPC API."""
        scheme = "https" if self.config.https else "http"
        return f"{scheme}://{self.config.host}:{self.port}"

    @property
    def proxy(self) -> ServerProxy:
        """Lazy-initialize XML-RPC proxy."""
        if self._proxy is None:
            self._proxy = ServerProxy(self.base_url)
        return self._proxy

    def close(self) -> None:
        """Close the XML-RPC proxy."""
        if self._proxy is not None:
            self._proxy("close")()
            self._proxy = None

    def __enter__(self) -> "XMLRPCClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def get_links(self, address: str | None = None) -> list[DeviceLink]:
        """Get all device links or links for a specific address.

        Args:
            address: Optional device/channel address to filter by

        Returns:
            List of device links
        """
        try:
            if address:
                result = self.proxy.getLinks(address, 0)
            else:
                result = self.proxy.getLinks("", 0)
        except Exception as e:
            raise XMLRPCError(f"Failed to get links: {e}") from e

        links = []
        for item in result:
            links.append(
                DeviceLink(
                    sender=item.get("SENDER", ""),
                    receiver=item.get("RECEIVER", ""),
                    name=item.get("NAME", ""),
                    description=item.get("DESCRIPTION", ""),
                )
            )
        return links

    def get_link_peers(self, address: str) -> list[str]:
        """Get all link peers for a channel.

        Args:
            address: Channel address (e.g., "000B5D89B014D8:1")

        Returns:
            List of peer addresses
        """
        try:
            return self.proxy.getLinkPeers(address)
        except Exception as e:
            raise XMLRPCError(f"Failed to get link peers: {e}") from e

    def add_link(
        self,
        sender: str,
        receiver: str,
        name: str = "",
        description: str = "",
    ) -> None:
        """Create a new device link (Direktverknüpfung).

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            name: Optional link name
            description: Optional link description

        Raises:
            XMLRPCError: If link creation fails
        """
        try:
            self.proxy.addLink(sender, receiver, name, description)
        except Exception as e:
            raise XMLRPCError(f"Failed to add link: {e}") from e

    def remove_link(self, sender: str, receiver: str) -> None:
        """Remove a device link.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address

        Raises:
            XMLRPCError: If link removal fails
        """
        try:
            self.proxy.removeLink(sender, receiver)
        except Exception as e:
            raise XMLRPCError(f"Failed to remove link: {e}") from e

    def get_link_info(self, sender: str, receiver: str) -> LinkInfo | None:
        """Get detailed information about a specific link.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address

        Returns:
            Link info or None if not found
        """
        try:
            result = self.proxy.getLinkInfo(sender, receiver)
            return LinkInfo(
                sender=result.get("SENDER", sender),
                receiver=result.get("RECEIVER", receiver),
                name=result.get("NAME", ""),
                description=result.get("DESCRIPTION", ""),
                flags=result.get("FLAGS", 0),
            )
        except Exception as e:
            # Link not found returns an error
            if "Unknown Link" in str(e):
                return None
            raise XMLRPCError(f"Failed to get link info: {e}") from e

    def get_paramset(
        self, address: str, paramset_key: str = "MASTER"
    ) -> dict[str, Any]:
        """Get a parameter set for a channel.

        Args:
            address: Channel address
            paramset_key: Paramset key (MASTER, VALUES, LINK, etc.)

        Returns:
            Dictionary of parameter values
        """
        try:
            return self.proxy.getParamset(address, paramset_key)
        except Exception as e:
            raise XMLRPCError(f"Failed to get paramset: {e}") from e

    def get_link_paramset(
        self, sender: str, receiver: str
    ) -> dict[str, Any]:
        """Get the LINK paramset for a device link.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address

        Returns:
            Dictionary of link parameter values
        """
        try:
            return self.proxy.getParamset(sender, receiver)
        except Exception as e:
            raise XMLRPCError(f"Failed to get link paramset: {e}") from e

    def set_link_paramset(
        self, sender: str, receiver: str, params: dict[str, Any]
    ) -> None:
        """Set parameters for a device link.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            params: Dictionary of parameter values to set
        """
        try:
            self.proxy.putParamset(sender, receiver, params)
        except Exception as e:
            raise XMLRPCError(f"Failed to set link paramset: {e}") from e

    def list_devices(self) -> list[dict[str, Any]]:
        """List all devices on this interface.

        Returns:
            List of device descriptions
        """
        try:
            return self.proxy.listDevices()
        except Exception as e:
            raise XMLRPCError(f"Failed to list devices: {e}") from e

    def get_device_description(self, address: str) -> dict[str, Any]:
        """Get device or channel description.

        Args:
            address: Device or channel address

        Returns:
            Device description dictionary
        """
        try:
            return self.proxy.getDeviceDescription(address)
        except Exception as e:
            raise XMLRPCError(f"Failed to get device description: {e}") from e
