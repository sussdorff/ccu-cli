"""Backend adapter for aiohomematic.

Provides a sync-friendly wrapper around the async aiohomematic API for CLI use.
"""

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from aiohomematic.central import CentralConfig, CentralUnit
from aiohomematic.const import ParamsetKey

from .config import CCUConfig
from .xmlrpc import DeviceLink, LinkInfo, XMLRPCClient


class BackendError(Exception):
    """Error from backend operations."""

    pass


@dataclass
class Device:
    """Simplified device representation for CLI."""

    address: str
    name: str
    model: str
    device_type: str
    interface: str
    firmware: str
    available: bool


@dataclass
class Channel:
    """Simplified channel representation for CLI."""

    address: str
    name: str
    channel_no: int


@dataclass
class DataPoint:
    """Simplified datapoint representation for CLI."""

    parameter: str
    value: Any
    unit: str | None
    writable: bool


@dataclass
class SysVar:
    """System variable representation."""

    name: str
    value: Any
    data_type: str
    unit: str | None


@dataclass
class Program:
    """Program representation from aiohomematic."""

    pid: str  # Unique ID
    name: str
    is_active: bool
    is_internal: bool
    last_execute_time: str | None


class CCUBackend:
    """Synchronous wrapper around aiohomematic for CLI use.

    This class provides a sync-friendly interface by running the async
    aiohomematic API in a dedicated event loop.
    """

    def __init__(self, config: CCUConfig):
        self.config = config
        self._central: CentralUnit | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_central_config(self) -> CentralConfig:
        """Create CentralConfig from CCUConfig."""
        return CentralConfig.for_ccu(
            name="ccu-cli",
            host=self.config.host,
            username=self.config.username or "",
            password=self.config.password or "",
            tls=self.config.https,
            verify_tls=False,  # Allow self-signed certs
        )

    def _run_async(self, coro: Any) -> Any:
        """Run an async coroutine in the event loop."""
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
        return self._loop.run_until_complete(coro)

    def start(self) -> None:
        """Start the backend connection."""
        if self._central is not None:
            return

        config = self._get_central_config()
        self._central = config.create_central()
        self._run_async(self._central.start())

    def stop(self) -> None:
        """Stop the backend connection."""
        if self._central is not None:
            self._run_async(self._central.stop())
            self._central = None
        if self._loop is not None:
            self._loop.close()
            self._loop = None

    def __enter__(self) -> "CCUBackend":
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()

    @property
    def central(self) -> CentralUnit:
        """Get the central unit, raising if not started."""
        if self._central is None:
            raise BackendError("Backend not started. Call start() first.")
        return self._central

    # Device operations

    def list_devices(self) -> list[Device]:
        """List all devices."""
        devices = []
        for device in self.central.devices:
            devices.append(
                Device(
                    address=device.address,
                    name=device.name or device.address,
                    model=device.model or "",
                    device_type=device.device_type or "",
                    interface=str(device.interface) if device.interface else "",
                    firmware=device.firmware or "",
                    available=device.available,
                )
            )
        return devices

    def get_device(self, address: str) -> Device | None:
        """Get a device by address."""
        device = self.central.get_device(address=address)
        if device is None:
            return None
        return Device(
            address=device.address,
            name=device.name or device.address,
            model=device.model or "",
            device_type=device.device_type or "",
            interface=str(device.interface) if device.interface else "",
            firmware=device.firmware or "",
            available=device.available,
        )

    def get_device_channels(self, address: str) -> list[Channel]:
        """Get channels for a device."""
        device = self.central.get_device(address=address)
        if device is None:
            return []
        channels = []
        for channel_no, channel in device.channels.items():
            channels.append(
                Channel(
                    address=channel.address,
                    name=channel.name or channel.address,
                    channel_no=channel_no,
                )
            )
        return channels

    def get_channel_datapoints(self, channel_address: str) -> list[DataPoint]:
        """Get datapoints for a channel."""
        # Parse channel address
        parts = channel_address.split(":")
        if len(parts) != 2:
            raise BackendError(f"Invalid channel address: {channel_address}")

        device_address = parts[0]
        channel_no = int(parts[1])

        device = self.central.get_device(address=device_address)
        if device is None:
            raise BackendError(f"Device not found: {device_address}")

        channel = device.channels.get(channel_no)
        if channel is None:
            raise BackendError(f"Channel not found: {channel_address}")

        datapoints = []
        for param_name, dp in channel.data_points.items():
            datapoints.append(
                DataPoint(
                    parameter=param_name,
                    value=dp.value,
                    unit=getattr(dp, "unit", None),
                    writable=getattr(dp, "is_writable", False),
                )
            )
        return datapoints

    def read_value(
        self,
        channel_address: str,
        parameter: str,
        paramset_key: ParamsetKey = ParamsetKey.VALUES,
    ) -> Any:
        """Read a parameter value from a channel."""

        async def _read() -> Any:
            return await self.central.get_value(
                channel_address=channel_address,
                paramset_key=paramset_key,
                parameter=parameter,
            )

        return self._run_async(_read())

    def write_value(
        self,
        channel_address: str,
        parameter: str,
        value: Any,
        paramset_key: ParamsetKey = ParamsetKey.VALUES,
    ) -> None:
        """Write a parameter value to a channel."""

        async def _write() -> None:
            await self.central.set_value(
                channel_address=channel_address,
                paramset_key=paramset_key,
                parameter=parameter,
                value=value,
            )

        self._run_async(_write())

    def get_paramset(
        self,
        channel_address: str,
        paramset_key: ParamsetKey = ParamsetKey.MASTER,
    ) -> dict[str, Any]:
        """Get a full paramset for a channel."""

        async def _get() -> dict[str, Any]:
            return await self.central.get_paramset(
                channel_address=channel_address,
                paramset_key=paramset_key,
            )

        return self._run_async(_get())

    # System variable operations

    def list_sysvars(self) -> list[SysVar]:
        """List all system variables."""
        sysvars = []
        for sysvar in self.central.hub.sysvars:
            sysvars.append(
                SysVar(
                    name=sysvar.name,
                    value=sysvar.value,
                    data_type=str(sysvar.data_type) if sysvar.data_type else "",
                    unit=getattr(sysvar, "unit", None),
                )
            )
        return sysvars

    def get_sysvar(self, name: str) -> SysVar | None:
        """Get a system variable by name."""
        sysvar = self.central.get_sysvar_by_name(sysvar_name=name)
        if sysvar is None:
            return None
        return SysVar(
            name=sysvar.name,
            value=sysvar.value,
            data_type=str(sysvar.data_type) if sysvar.data_type else "",
            unit=getattr(sysvar, "unit", None),
        )

    def set_sysvar(self, name: str, value: Any) -> None:
        """Set a system variable value."""
        sysvar = self.central.get_sysvar_by_name(sysvar_name=name)
        if sysvar is None:
            raise BackendError(f"System variable not found: {name}")

        async def _set() -> None:
            await sysvar.set_value(value)

        self._run_async(_set())

    # Program operations

    def list_programs(self) -> list[Program]:
        """List all programs."""
        programs = []
        for program in self.central.hub.programs:
            programs.append(
                Program(
                    pid=program.unique_id,
                    name=program.name,
                    is_active=program.is_active,
                    is_internal=program.is_internal,
                    last_execute_time=None,  # Not exposed directly in aiohomematic
                )
            )
        return programs

    def get_program(self, name: str) -> Program | None:
        """Get a program by name."""
        program = self.central.get_program_by_name(program_name=name)
        if program is None:
            return None
        return Program(
            pid=program.unique_id,
            name=program.name,
            is_active=program.is_active,
            is_internal=program.is_internal,
            last_execute_time=None,
        )

    def set_program_active(self, name: str, active: bool) -> None:
        """Enable or disable a program."""
        program = self.central.get_program_by_name(program_name=name)
        if program is None:
            raise BackendError(f"Program not found: {name}")

        async def _set() -> None:
            await program.set_active(active)

        self._run_async(_set())

    def refresh_data(self) -> None:
        """Refresh all data from the CCU."""

        async def _refresh() -> None:
            await self.central.hub.fetch_program_data()
            await self.central.hub.fetch_sysvar_data()

        self._run_async(_refresh())

    # Link operations (Direktverknüpfungen)

    def get_link_peers(self, address: str) -> list[str]:
        """Get link peers for a channel.

        Args:
            address: Channel address (e.g., "000B5D89B014D8:1")

        Returns:
            List of peer addresses
        """

        async def _get_peers() -> list[str]:
            return await self.central.get_link_peers(address=address)

        return self._run_async(_get_peers())

    def create_link(
        self,
        sender: str,
        receiver: str,
        name: str = "",
        description: str = "",
    ) -> None:
        """Create a device link (Direktverknüpfung).

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            name: Optional link name
            description: Optional link description
        """

        async def _add_link() -> None:
            await self.central.add_link(
                sender_address=sender,
                receiver_address=receiver,
                name=name,
                description=description,
            )

        self._run_async(_add_link())

    def delete_link(self, sender: str, receiver: str) -> None:
        """Remove a device link.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
        """

        async def _remove_link() -> None:
            await self.central.remove_link(
                sender_address=sender,
                receiver_address=receiver,
            )

        self._run_async(_remove_link())

    def list_links(
        self, address: str | None = None, interface: str = "HmIP-RF"
    ) -> list[DeviceLink]:
        """List device links with full details (name, description).

        Uses XML-RPC because aiohomematic only returns peer addresses,
        not the full link metadata.

        Args:
            address: Optional filter by device/channel address
            interface: Interface to use ("HmIP-RF" or "BidCos-RF")

        Returns:
            List of device links with full details
        """
        with XMLRPCClient(self.config, interface) as client:
            return client.get_links(address)

    def get_link(
        self, sender: str, receiver: str, interface: str = "HmIP-RF"
    ) -> LinkInfo | None:
        """Get detailed information about a specific link.

        Uses XML-RPC for detailed link info including flags.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            interface: Interface to use

        Returns:
            Link info or None if not found
        """
        with XMLRPCClient(self.config, interface) as client:
            return client.get_link_info(sender, receiver)

    def get_link_paramset(
        self, sender: str, receiver: str, interface: str = "HmIP-RF"
    ) -> dict[str, Any]:
        """Get the LINK paramset for a device link.

        Link paramsets can exist on both sides of the link:
        - Sender side: getParamset(sender, receiver) - button/switch profiles
        - Receiver side: getParamset(receiver, sender) - actuator profiles

        This method returns both combined with prefixes to distinguish them.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            interface: Interface to use

        Returns:
            Dictionary with 'sender' and 'receiver' keys containing paramsets
        """
        with XMLRPCClient(self.config, interface) as client:
            result: dict[str, Any] = {}

            # Get sender-side paramset (button profiles)
            sender_params = client.get_link_paramset(sender, receiver)
            if sender_params:
                result["sender"] = sender_params

            # Get receiver-side paramset (actuator profiles)
            receiver_params = client.get_link_paramset(receiver, sender)
            if receiver_params:
                result["receiver"] = receiver_params

            return result

    def set_link_paramset(
        self,
        sender: str,
        receiver: str,
        params: dict[str, Any],
        interface: str = "HmIP-RF",
    ) -> None:
        """Set parameters for a device link.

        Uses XML-RPC for paramset access.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            params: Dictionary of parameter values to set
            interface: Interface to use
        """
        with XMLRPCClient(self.config, interface) as client:
            client.set_link_paramset(sender, receiver, params)


@contextmanager
def get_backend(config: CCUConfig) -> Iterator[CCUBackend]:
    """Context manager for backend access."""
    backend = CCUBackend(config)
    try:
        backend.start()
        yield backend
    finally:
        backend.stop()
