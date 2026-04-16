"""Backend adapter for aiohomematic.

Provides a sync-friendly wrapper around the async aiohomematic API for CLI use.
Uses ReGa client for operations not available in aiohomematic (e.g., delete_program).
"""

import asyncio
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from aiohomematic.central import CentralConfig, CentralUnit
from aiohomematic.const import Interface, ParamsetKey

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
    interface: str
    firmware: str
    available: bool


@dataclass
class Channel:
    """Simplified channel representation for CLI."""

    address: str
    name: str
    channel_no: int
    channel_type: str = ""


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


@dataclass
class HeatingGroupMember:
    """A member device of a heating group."""

    address: str
    member_type: str
    name: str
    model: str


class CCUBackend:
    """Synchronous wrapper around aiohomematic for CLI use.

    This class provides a sync-friendly interface by running the async
    aiohomematic API in a dedicated event loop.
    """

    def __init__(self, config: CCUConfig, include_virtual_devices: bool = False):
        self.config = config
        self.include_virtual_devices = include_virtual_devices
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
            enable_virtual_devices=self.include_virtual_devices,
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

        async def _start() -> None:
            config = self._get_central_config()
            # create_central() is async since aiohomematic 2026.2.x
            self._central = await config.create_central()
            await self._central.start()

        self._run_async(_start())

    def stop(self) -> None:
        """Stop the backend connection.

        Suppresses aiohomematic warnings during shutdown to avoid noise from
        expected disconnection errors in background tasks.
        """
        if self._central is not None:
            # Suppress aiohomematic warnings during shutdown
            # Background tasks may fail with connection errors which is expected
            aiohomematic_logger = logging.getLogger("aiohomematic")
            original_level = aiohomematic_logger.level
            aiohomematic_logger.setLevel(logging.ERROR)
            try:
                self._run_async(self._central.stop())
            finally:
                aiohomematic_logger.setLevel(original_level)
            self._central = None
        if self._loop is not None:
            # Cancel any remaining tasks to avoid "Task was destroyed" warnings
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            # Give cancelled tasks a chance to complete
            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
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
                    interface=str(device.interface) if device.interface else "",
                    firmware=device.firmware or "",
                    available=device.available,
                )
            )
        return devices

    def get_device(self, address: str) -> Device | None:
        """Get a device by address."""
        device = self.central.device_registry.get_device(address=address)
        if device is None:
            return None
        return Device(
            address=device.address,
            name=device.name or device.address,
            model=device.model or "",
            interface=str(device.interface) if device.interface else "",
            firmware=device.firmware or "",
            available=device.available,
        )

    def get_device_channels(self, address: str) -> list[Channel]:
        """Get channels for a device."""
        device = self.central.device_registry.get_device(address=address)
        if device is None:
            return []
        channels = []
        for channel_no, channel in device.channels.items():
            channel_type = channel.description.get("TYPE", "") if channel.description else ""
            channels.append(
                Channel(
                    address=channel.address,
                    name=channel.name or channel.address,
                    channel_no=channel_no,
                    channel_type=channel_type,
                )
            )
        return channels

    def list_groups(self) -> list[Device]:
        """List heating groups from the VirtualDevices interface."""
        group_definitions = self._safe_get_heating_group_definitions()
        groups = {
            device.address: self._apply_group_display_name(
                device=device,
                group_definitions=group_definitions,
            )
            for device in self.list_devices()
            if device.interface == Interface.VIRTUAL_DEVICES.value
        }

        for raw_device in self._list_group_devices_raw():
            address = str(raw_device.get("ADDRESS", ""))
            if not address or ":" in address or address in groups:
                continue
            groups[address] = self._build_group_from_xmlrpc(
                address=address,
                raw_device=raw_device,
                group_definitions=group_definitions,
            )

        return sorted(
            groups.values(),
            key=lambda device: (device.name.lower(), device.address),
        )

    def get_group(self, address: str) -> Device | None:
        """Get a heating group by address."""
        device = self.get_device(address)
        group_definitions = self._safe_get_heating_group_definitions()
        if device is not None and device.interface == Interface.VIRTUAL_DEVICES.value:
            return self._apply_group_display_name(
                device=device,
                group_definitions=group_definitions,
            )

        for raw_device in self._list_group_devices_raw():
            if raw_device.get("ADDRESS") != address:
                continue
            return self._build_group_from_xmlrpc(
                address=address,
                raw_device=raw_device,
                group_definitions=group_definitions,
            )
        return None

    def get_group_channels(self, address: str) -> list[Channel]:
        """Get channels for a heating group."""
        channels = self.get_device_channels(address)
        if channels:
            return channels
        if self.get_group(address) is None:
            return []

        description = self._get_group_device_description(address)
        if not description:
            return []

        channels = [
            Channel(
                address=address,
                name=address,
                channel_no=address,
                channel_type=str(description.get("TYPE", "")),
            )
        ]
        for child_address in description.get("CHILDREN", []):
            child_description = self._get_group_device_description(child_address)
            channels.append(
                Channel(
                    address=child_address,
                    name=child_address.split(":", 1)[-1],
                    channel_no=child_description.get(
                        "INDEX",
                        child_address.split(":", 1)[-1],
                    ),
                    channel_type=str(child_description.get("TYPE", "")),
                )
            )
        return channels

    def get_group_members(self, address: str) -> list[HeatingGroupMember]:
        """Get member devices for a heating group."""
        definition = self._safe_get_heating_group_definitions().get(address)
        if definition is None:
            return []

        members = []
        for member in definition.get("groupMembers", []):
            member_address = str(member.get("id", ""))
            member_type = str(member.get("memberType", {}).get("id", ""))
            device_address = member_address.split(":", 1)[0]
            device = self.central.device_registry.get_device(address=device_address)
            members.append(
                HeatingGroupMember(
                    address=member_address,
                    member_type=member_type,
                    name=(device.name or member_address) if device is not None else member_address,
                    model=(device.model or "") if device is not None else "",
                )
            )
        return members

    def _safe_get_heating_group_definitions(self) -> dict[str, dict[str, Any]]:
        """Return heating-group definitions from CCU JSON-RPC."""
        try:
            response = self._run_async(
                self.central.json_rpc_client._post(method="CCU.getHeatingGroupList")
            )
            raw_result = response.get("result", {})
            payload = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
        except Exception:
            logging.getLogger(__name__).debug(
                "Failed to load heating group definitions",
                exc_info=True,
            )
            return {}

        definitions = {}
        for group in payload.get("groups", []):
            try:
                group_id = int(group["id"])
            except (KeyError, TypeError, ValueError):
                continue
            definitions[f"INT{group_id:07d}"] = group
        return definitions

    def _list_group_devices_raw(self) -> list[dict[str, Any]]:
        """Return raw VirtualDevices entries from the XML-RPC groups interface."""
        try:
            with XMLRPCClient(self.config, interface="VirtualDevices") as client:
                return client.list_devices()
        except Exception:
            logging.getLogger(__name__).debug(
                "Failed to list raw virtual devices",
                exc_info=True,
            )
            return []

    def _get_group_device_description(self, address: str) -> dict[str, Any]:
        """Return the raw XML-RPC device description for a virtual group object."""
        try:
            with XMLRPCClient(self.config, interface="VirtualDevices") as client:
                return client.get_device_description(address)
        except Exception:
            logging.getLogger(__name__).debug(
                "Failed to get raw virtual device description",
                exc_info=True,
            )
            return {}

    def _build_group_from_xmlrpc(
        self,
        *,
        address: str,
        raw_device: dict[str, Any],
        group_definitions: dict[str, dict[str, Any]],
    ) -> Device:
        """Build a group device from raw `/groups` XML-RPC data."""
        display_name = self._get_group_display_name(
            address=address,
            raw_name=address,
            group_definitions=group_definitions,
        )
        return Device(
            address=address,
            name=display_name,
            model=str(raw_device.get("TYPE", "")),
            interface=Interface.VIRTUAL_DEVICES.value,
            firmware=str(raw_device.get("FIRMWARE", "")),
            available=True,
        )

    def _apply_group_display_name(
        self,
        *,
        device: Device,
        group_definitions: dict[str, dict[str, Any]],
    ) -> Device:
        """Apply the configured heating-group name when available."""
        display_name = self._get_group_display_name(
            address=device.address,
            raw_name=device.name,
            group_definitions=group_definitions,
        )
        if display_name == device.name:
            return device

        return Device(
            address=device.address,
            name=display_name,
            model=device.model,
            interface=device.interface,
            firmware=device.firmware,
            available=device.available,
        )

    def _get_group_display_name(
        self,
        *,
        address: str,
        raw_name: str,
        group_definitions: dict[str, dict[str, Any]],
    ) -> str:
        """Return the configured group name when available."""
        definition = group_definitions.get(address)
        if definition is None:
            return raw_name

        properties = definition.get("groupProperties", {})
        return (
            str(properties.get("GROUP_DEVICE_NAME", "")).strip()
            or str(properties.get("NAME", "")).strip()
            or raw_name
        )

    def rename_device(
        self, address: str, new_name: str, include_channels: bool = False
    ) -> bool:
        """Rename a device.

        Args:
            address: Device address (e.g., "001098A98B1682")
            new_name: New name for the device
            include_channels: If True, also rename channels to "name:channel_no"

        Returns:
            True if successful, False if device not found

        Raises:
            BackendError: If rename fails
        """
        # Check device exists first
        device = self.central.device_registry.get_device(address=address)
        if device is None:
            return False

        async def _rename() -> None:
            # Note: rename_device may return False even when successful (API quirk)
            await self.central.rename_device(
                device_address=address,
                name=new_name,
                include_channels=include_channels,
            )

        self._run_async(_rename())
        return True

    def get_channel_datapoints(self, channel_address: str) -> list[DataPoint]:
        """Get datapoints for a channel."""
        # Parse channel address
        parts = channel_address.split(":")
        if len(parts) != 2:
            raise BackendError(f"Invalid channel address: {channel_address}")

        device_address = parts[0]
        channel_no = int(parts[1])

        device = self.central.device_registry.get_device(address=device_address)
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
        for sysvar in self.central.hub_coordinator.sysvar_data_points:
            sysvars.append(
                SysVar(
                    name=sysvar.name,
                    value=sysvar.value,
                    data_type=str(sysvar.data_type) if hasattr(sysvar, "data_type") and sysvar.data_type else "",
                    unit=getattr(sysvar, "unit", None),
                )
            )
        return sysvars

    def get_sysvar(self, name: str) -> SysVar | None:
        """Get a system variable by name."""
        sysvar = self.central.hub_coordinator.get_system_variable(name=name)
        if sysvar is None:
            return None
        return SysVar(
            name=sysvar.name,
            value=sysvar.value,
            data_type=str(sysvar.data_type) if hasattr(sysvar, "data_type") and sysvar.data_type else "",
            unit=getattr(sysvar, "unit", None),
        )

    def set_sysvar(self, name: str, value: Any) -> None:
        """Set a system variable value."""
        async def _set() -> None:
            await self.central.hub_coordinator.set_system_variable(name=name, value=value)

        self._run_async(_set())

    # Program operations

    def list_programs(self) -> list[Program]:
        """List all programs."""
        programs = []
        # Get unique programs via their switch data point (one per program)
        # program_data_points returns a tuple of all program data points (buttons + switches)
        seen_pids: set[str] = set()
        for dp in self.central.hub_coordinator.program_data_points:
            # Each program has a switch data point with the is_active/is_internal properties
            pid = getattr(dp, "pid", None)
            if pid is None or pid in seen_pids:
                continue
            seen_pids.add(pid)
            # Only switches have is_active property; buttons don't
            if not hasattr(dp, "is_active"):
                continue
            programs.append(
                Program(
                    pid=pid,
                    name=dp.name,
                    is_active=dp.is_active,
                    is_internal=dp.is_internal,
                    last_execute_time=None,
                )
            )
        return programs

    def _get_program_dp(self, id_or_name: str) -> Any:
        """Get a program data point (the switch) by ID or name."""
        # Try by ID (pid) first
        program_type = self.central.hub_coordinator.get_program_data_point(pid=id_or_name)
        if program_type is None:
            # Try by legacy_name (the display name)
            program_type = self.central.hub_coordinator.get_program_data_point(legacy_name=id_or_name)
        if program_type is None:
            return None
        # Return the switch which has the program state (is_active, is_internal)
        return program_type.switch

    def get_program(self, id_or_name: str) -> Program | None:
        """Get a program by ID or name.

        Args:
            id_or_name: Program ID (unique_id) or name

        Returns:
            Program object or None if not found
        """
        program = self._get_program_dp(id_or_name)
        if program is None:
            return None
        return Program(
            pid=program.pid,
            name=program.name,
            is_active=program.is_active,
            is_internal=program.is_internal,
            last_execute_time=None,
        )

    def run_program(self, id_or_name: str) -> None:
        """Execute a program.

        Args:
            id_or_name: Program ID (unique_id) or name

        Raises:
            BackendError: If program not found
        """
        program = self._get_program_dp(id_or_name)
        if program is None:
            raise BackendError(f"Program not found: {id_or_name}")

        async def _run() -> None:
            await self.central.hub_coordinator.execute_program(pid=program.pid)

        self._run_async(_run())

    def set_program_active(self, id_or_name: str, active: bool) -> None:
        """Enable or disable a program.

        Args:
            id_or_name: Program ID (unique_id) or name
            active: True to enable, False to disable

        Raises:
            BackendError: If program not found
        """
        program = self._get_program_dp(id_or_name)
        if program is None:
            raise BackendError(f"Program not found: {id_or_name}")

        async def _set() -> None:
            await self.central.hub_coordinator.set_program_state(pid=program.pid, state=active)

        self._run_async(_set())

    def delete_program(self, id_or_name: str) -> str:
        """Delete a program.

        Note: Uses ReGa client since aiohomematic doesn't support program deletion.

        Args:
            id_or_name: Program ID (unique_id) or name

        Returns:
            Name of the deleted program

        Raises:
            BackendError: If program not found or deletion fails
        """
        from .rega import ReGaClient, ReGaError

        # First find the program via aiohomematic to get details
        program = self.get_program(id_or_name)
        if program is None:
            raise BackendError(f"Program not found: {id_or_name}")

        # Use ReGa to delete (requires numeric ID)
        # The pid from aiohomematic is the unique_id string, we need to extract the numeric part
        # unique_id format is typically just the numeric ID as a string
        try:
            program_id = int(program.pid)
        except ValueError:
            raise BackendError(f"Cannot delete program: invalid ID format '{program.pid}'")

        with ReGaClient(self.config) as rega:
            try:
                rega.delete_program(program_id)
            except ReGaError as e:
                raise BackendError(f"Failed to delete program: {e}")

        return program.name

    def refresh_data(self) -> None:
        """Refresh all data from the CCU."""

        async def _refresh() -> None:
            await self.central.hub_coordinator.fetch_program_data()
            await self.central.hub_coordinator.fetch_sysvar_data()

        self._run_async(_refresh())

    # Install mode / Pairing operations

    def get_install_mode(self, interface: Interface) -> int:
        """Get remaining time in install mode for an interface.

        Args:
            interface: The interface to check (e.g., Interface.HMIP_RF)

        Returns:
            Remaining seconds in install mode, 0 if not active
        """

        async def _get() -> int:
            return await self.central.get_install_mode(interface=interface)

        return self._run_async(_get())

    def set_install_mode(
        self,
        interface: Interface,
        on: bool = True,
        time: int = 60,
        mode: int = 1,
        device_address: str | None = None,
    ) -> bool:
        """Set install mode (pairing mode) on an interface.

        Args:
            interface: The interface to set install mode on
            on: True to enable, False to disable
            time: Duration in seconds (default 60)
            mode: 1=normal, 2=set all ROAMING devices into install mode
            device_address: Optional, limit pairing to specific device

        Returns:
            True if successful
        """

        async def _set() -> bool:
            return await self.central.set_install_mode(
                interface=interface,
                on=on,
                time=time,
                mode=mode,
                device_address=device_address,
            )

        return self._run_async(_set())

    # Inbox operations

    def list_inbox_devices(self) -> list[Device]:
        """List devices waiting in the CCU inbox.

        Returns:
            List of devices in inbox (not yet accepted)
        """

        async def _fetch_and_list() -> list[Device]:
            # Fetch latest inbox data
            await self.central.hub_coordinator.fetch_inbox_data(scheduled=False)

            # Access inbox_dp via the internal _hub
            hub = self.central.hub_coordinator._hub  # type: ignore[attr-defined]
            inbox_dp = hub.inbox_dp

            if inbox_dp is None:
                return []

            devices = []
            for inbox_device in inbox_dp.devices:
                devices.append(
                    Device(
                        address=inbox_device.address,
                        name=inbox_device.name or inbox_device.address,
                        model=inbox_device.device_type or "",
                        interface=inbox_device.interface or "",
                        firmware="",
                        available=True,
                    )
                )
            return devices

        return self._run_async(_fetch_and_list())

    def accept_inbox_device(self, device_address: str) -> bool:
        """Accept a device from the CCU inbox.

        Args:
            device_address: Address of the device to accept

        Returns:
            True if successful
        """

        async def _accept() -> bool:
            return await self.central.accept_device_in_inbox(
                device_address=device_address
            )

        return self._run_async(_accept())

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
        interface: str = "HmIP-RF",
    ) -> None:
        """Create a device link (Direktverknüpfung).

        Uses XML-RPC because aiohomematic does not expose addLink.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            name: Optional link name
            description: Optional link description
            interface: Interface to use ("HmIP-RF" or "BidCos-RF")
        """
        with XMLRPCClient(self.config, interface) as client:
            client.add_link(sender, receiver, name, description)

    def delete_link(
        self,
        sender: str,
        receiver: str,
        interface: str = "HmIP-RF",
    ) -> None:
        """Remove a device link.

        Uses XML-RPC because aiohomematic does not expose removeLink.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            interface: Interface to use ("HmIP-RF" or "BidCos-RF")
        """
        with XMLRPCClient(self.config, interface) as client:
            client.remove_link(sender, receiver)

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
        side: str = "receiver",
        interface: str = "HmIP-RF",
    ) -> None:
        """Set parameters for a device link.

        Uses XML-RPC for paramset access.

        Args:
            sender: Sender channel address
            receiver: Receiver channel address
            params: Dictionary of parameter values to set
            side: Which side to set params on ("sender" or "receiver")
            interface: Interface to use
        """
        with XMLRPCClient(self.config, interface) as client:
            if side == "receiver":
                # Set on receiver side (actuator profiles)
                client.set_link_paramset(receiver, sender, params)
            else:
                # Set on sender side (button profiles)
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
