"""CLI interface for ccu-cli."""

import sys
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from .backend import CCUBackend, BackendError
from .config import ConfigurationError, load_config
from .rega import ReGaClient, ReGaError

console = Console()
error_console = Console(stderr=True)


def get_backend() -> CCUBackend:
    """Create a CCU backend with loaded configuration.

    Raises:
        SystemExit: If required configuration is missing
    """
    config = load_config()
    try:
        config.validate()
    except ConfigurationError as e:
        error_console.print(f"[red]Configuration Error:[/red] {e}")
        sys.exit(1)
    return CCUBackend(config)


def get_rega_client() -> ReGaClient:
    """Create a ReGa client with loaded configuration.

    Raises:
        SystemExit: If required configuration is missing
    """
    config = load_config()
    try:
        config.validate()
    except ConfigurationError as e:
        error_console.print(f"[red]Configuration Error:[/red] {e}")
        sys.exit(1)
    return ReGaClient(config)


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    import json

    console.print_json(json.dumps(data))


def _format_timestamp(ts: int | str | None) -> str:
    """Format Unix timestamp for display."""
    if ts is None:
        return "N/A"
    if isinstance(ts, str):
        return ts if ts else "Never"
    if ts == 0:
        return "Never"
    from datetime import datetime

    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


@click.group()
@click.version_option()
def main() -> None:
    """CLI tool for interacting with RaspberryMatic/CCU3."""
    pass


@main.command()
def info() -> None:
    """Show CCU server information."""
    with get_backend() as backend:
        try:
            # Show basic info from central
            table = Table(title="CCU Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Host", backend.config.host)
            table.add_row("Devices", str(len(backend.list_devices())))
            table.add_row("System Variables", str(len(backend.list_sysvars())))
            table.add_row("Programs", str(len(backend.list_programs())))

            console.print(table)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


# =============================================================================
# Device Commands
# =============================================================================


@main.group()
def device() -> None:
    """Manage CCU devices."""
    pass


@device.command("list")
def device_list() -> None:
    """List all devices."""
    with get_backend() as backend:
        try:
            devices = backend.list_devices()

            table = Table(title="Devices")
            table.add_column("Address", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Model", style="yellow")
            table.add_column("Available", style="magenta")

            for dev in devices:
                available = "✓" if dev.available else "✗"
                table.add_row(dev.address, dev.name, dev.model, available)

            console.print(table)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@device.command("get")
@click.argument("address")
def device_get(address: str) -> None:
    """Show device details.

    ADDRESS: Device serial/address (e.g., 000A1B2C3D4E5F)
    """
    with get_backend() as backend:
        try:
            dev = backend.get_device(address)
            if dev is None:
                error_console.print(f"[red]Error:[/red] Device not found: {address}")
                sys.exit(1)

            # Device info table
            info_table = Table(title=f"Device: {dev.name}")
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="green")

            info_table.add_row("Address", dev.address)
            info_table.add_row("Name", dev.name)
            info_table.add_row("Model", dev.model)
            info_table.add_row("Interface", dev.interface)
            info_table.add_row("Firmware", dev.firmware)
            info_table.add_row("Available", "Yes" if dev.available else "No")

            console.print(info_table)

            # Channels table
            channels = backend.get_device_channels(address)
            if channels:
                console.print()
                ch_table = Table(title="Channels")
                ch_table.add_column("No", style="cyan")
                ch_table.add_column("Type", style="magenta")
                ch_table.add_column("Address", style="yellow")
                ch_table.add_column("Name", style="green")

                for ch in channels:
                    ch_table.add_row(str(ch.channel_no), ch.channel_type, ch.address, ch.name)

                console.print(ch_table)

        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@device.command("rename")
@click.argument("address")
@click.argument("new_name")
@click.option(
    "--include-channels",
    is_flag=True,
    help="Also rename channels to 'name:channel_no' format",
)
def device_rename(address: str, new_name: str, include_channels: bool) -> None:
    """Rename a device.

    ADDRESS: Device address (e.g., 001098A98B1682)
    NEW_NAME: New name for the device
    """
    with get_backend() as backend:
        try:
            success = backend.rename_device(address, new_name, include_channels)
            if success:
                console.print(f"[green]OK[/green] Renamed device {address} to '{new_name}'")
                if include_channels:
                    console.print("[dim]Channels renamed to 'name:channel_no' format[/dim]")
            else:
                error_console.print(f"[red]Error:[/red] Device not found: {address}")
                sys.exit(1)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@device.command("config")
@click.argument("channel_address")
def device_config(channel_address: str) -> None:
    """Show channel configuration (MASTER parameters).

    CHANNEL_ADDRESS format: <address>:<channel>
    Example: 000A1B2C3D4E5F:0
    """
    with get_backend() as backend:
        try:
            data = backend.get_paramset(channel_address)
            print_json(data)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@device.command("refresh")
def device_refresh() -> None:
    """Reload hub data (programs, sysvars) from CCU."""
    with get_backend() as backend:
        try:
            backend.refresh_data()
            console.print("[green]OK[/green] Data refreshed")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


# =============================================================================
# Datapoint Commands
# =============================================================================


@main.group()
def datapoint() -> None:
    """Read and write datapoint values."""
    pass


@datapoint.command("get")
@click.argument("path")
def datapoint_get(path: str) -> None:
    """Read a datapoint value.

    PATH format: <address>:<channel>/<datapoint>
    Example: 000A1B2C3D4E5F:1/TEMPERATURE
    """
    try:
        # Parse path: address:channel/datapoint
        if "/" not in path:
            raise click.BadParameter("Path must be <address>:<channel>/<datapoint>")
        channel_part, datapoint_name = path.rsplit("/", 1)
        if ":" not in channel_part:
            raise click.BadParameter("Path must be <address>:<channel>/<datapoint>")
        channel_address = channel_part
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] Invalid path format: {e}")
        sys.exit(1)

    with get_backend() as backend:
        try:
            value = backend.read_value(channel_address, datapoint_name)
            console.print(value)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@datapoint.command("set")
@click.argument("path")
@click.argument("value")
def datapoint_set(path: str, value: str) -> None:
    """Set a datapoint value.

    PATH format: <address>:<channel>/<datapoint>
    Example: ccu datapoint set 000A1B2C3D4E5F:1/STATE true
    """
    try:
        # Parse path: address:channel/datapoint
        if "/" not in path:
            raise click.BadParameter("Path must be <address>:<channel>/<datapoint>")
        channel_part, datapoint_name = path.rsplit("/", 1)
        if ":" not in channel_part:
            raise click.BadParameter("Path must be <address>:<channel>/<datapoint>")
        channel_address = channel_part
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] Invalid path format: {e}")
        sys.exit(1)

    # Parse value to appropriate type
    parsed_value: Any
    if value.lower() == "true":
        parsed_value = True
    elif value.lower() == "false":
        parsed_value = False
    else:
        try:
            parsed_value = int(value)
        except ValueError:
            try:
                parsed_value = float(value)
            except ValueError:
                parsed_value = value

    with get_backend() as backend:
        try:
            backend.write_value(channel_address, datapoint_name, parsed_value)
            console.print(f"[green]OK[/green] {path} = {parsed_value}")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


# =============================================================================
# Sysvar Commands
# =============================================================================


@main.group()
def sysvar() -> None:
    """Manage system variables."""
    pass


@sysvar.command("list")
def sysvar_list() -> None:
    """List all system variables."""
    with get_backend() as backend:
        try:
            sysvars = backend.list_sysvars()

            table = Table(title="System Variables")
            table.add_column("Name", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Unit", style="magenta")

            for sv in sysvars:
                table.add_row(
                    sv.name,
                    str(sv.value),
                    sv.data_type,
                    sv.unit or "",
                )

            console.print(table)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


# =============================================================================
# Program Commands
# =============================================================================


@main.group()
def program() -> None:
    """Manage CCU programs."""
    pass


@program.command("list")
def program_list() -> None:
    """List all programs."""
    with get_backend() as backend:
        try:
            programs = backend.list_programs()

            table = Table(title="Programs")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Active", style="yellow")
            table.add_column("Internal", style="magenta")

            for prg in programs:
                if prg.is_internal:
                    continue  # Skip internal programs by default
                active_str = "✓" if prg.is_active else "✗"
                internal_str = "✓" if prg.is_internal else ""
                table.add_row(
                    prg.pid,
                    prg.name,
                    active_str,
                    internal_str,
                )

            console.print(table)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@program.command("get")
@click.argument("id_or_name")
def program_get(id_or_name: str) -> None:
    """Show program details.

    ID_OR_NAME can be a program ID or the program name.
    """
    with get_backend() as backend:
        try:
            prg = backend.get_program(id_or_name)
            if prg is None:
                error_console.print(f"[red]Error:[/red] Program not found: {id_or_name}")
                sys.exit(1)

            table = Table(title=f"Program: {prg.name}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("ID", prg.pid)
            table.add_row("Name", prg.name)
            table.add_row("Active", "Yes" if prg.is_active else "No")
            table.add_row("Internal", "Yes" if prg.is_internal else "No")
            table.add_row("Last Executed", _format_timestamp(prg.last_execute_time))

            console.print(table)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@program.command("run")
@click.argument("id_or_name")
def program_run(id_or_name: str) -> None:
    """Execute a program.

    ID_OR_NAME can be a program ID or the program name.
    """
    with get_backend() as backend:
        try:
            # Get program first to show its name in output
            prg = backend.get_program(id_or_name)
            if prg is None:
                error_console.print(f"[red]Error:[/red] Program not found: {id_or_name}")
                sys.exit(1)
            backend.run_program(id_or_name)
            console.print(f"[green]OK[/green] Program '{prg.name}' executed")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@program.command("delete")
@click.argument("id_or_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def program_delete(id_or_name: str, yes: bool) -> None:
    """Delete a program.

    ID_OR_NAME can be a program ID or the program name.
    """
    with get_backend() as backend:
        try:
            # Get program first to show its name in confirmation
            prg = backend.get_program(id_or_name)
            if prg is None:
                error_console.print(f"[red]Error:[/red] Program not found: {id_or_name}")
                sys.exit(1)

            if not yes:
                if not click.confirm(
                    f"Are you sure you want to delete program '{prg.name}' (ID: {prg.pid})?"
                ):
                    console.print("Cancelled")
                    return

            deleted_name = backend.delete_program(id_or_name)
            console.print(f"[green]OK[/green] Deleted program '{deleted_name}'")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@program.command("enable")
@click.argument("id_or_name")
def program_enable(id_or_name: str) -> None:
    """Enable a program.

    ID_OR_NAME can be a program ID or the program name.
    """
    with get_backend() as backend:
        try:
            # Get program first to show its name in output
            prg = backend.get_program(id_or_name)
            if prg is None:
                error_console.print(f"[red]Error:[/red] Program not found: {id_or_name}")
                sys.exit(1)
            backend.set_program_active(id_or_name, True)
            console.print(f"[green]OK[/green] Program '{prg.name}' enabled")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@program.command("disable")
@click.argument("id_or_name")
def program_disable(id_or_name: str) -> None:
    """Disable a program.

    ID_OR_NAME can be a program ID or the program name.
    """
    with get_backend() as backend:
        try:
            # Get program first to show its name in output
            prg = backend.get_program(id_or_name)
            if prg is None:
                error_console.print(f"[red]Error:[/red] Program not found: {id_or_name}")
                sys.exit(1)
            backend.set_program_active(id_or_name, False)
            console.print(f"[green]OK[/green] Program '{prg.name}' disabled")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


# =============================================================================
# Room Commands
# =============================================================================


@main.group()
def room() -> None:
    """Manage CCU rooms."""
    pass


@room.command("list")
def room_list() -> None:
    """List all rooms."""
    with get_rega_client() as client:
        try:
            rooms = client.list_rooms()

            table = Table(title="Rooms")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")

            for rm in rooms:
                table.add_row(str(rm["id"]), rm["name"])

            console.print(table)
        except ReGaError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@room.command("get")
@click.argument("room_id", type=int)
def room_get(room_id: int) -> None:
    """Show room details including devices.

    ROOM_ID: The room's internal ID
    """
    with get_rega_client() as client:
        try:
            # Get room info by listing all rooms and finding the one we want
            rooms = client.list_rooms()
            room_info = next((r for r in rooms if r["id"] == room_id), None)
            if room_info is None:
                error_console.print(f"[red]Error:[/red] Room not found: {room_id}")
                sys.exit(1)

            # Show room info
            console.print(f"[bold]Room:[/bold] {room_info['name']} (ID: {room_id})")
            console.print()

            # List devices in the room
            devices = client.list_room_devices(room_id)
            if devices:
                table = Table(title="Devices in Room")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Address", style="yellow")

                for dev in devices:
                    table.add_row(str(dev.id), dev.name, dev.address)

                console.print(table)
            else:
                console.print("No devices in this room.")

        except ReGaError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@room.command("rename")
@click.argument("room_id", type=int)
@click.argument("new_name")
def room_rename(room_id: int, new_name: str) -> None:
    """Rename an existing room."""
    with get_rega_client() as client:
        try:
            client.rename_room(room_id, new_name)
            console.print(f"[green]OK[/green] Renamed room {room_id} to '{new_name}'")
        except ReGaError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@room.command("delete")
@click.argument("room_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def room_delete(room_id: int, yes: bool) -> None:
    """Delete a room."""
    if not yes:
        if not click.confirm(f"Are you sure you want to delete room {room_id}?"):
            console.print("Cancelled")
            return

    with get_rega_client() as client:
        try:
            client.delete_room(room_id)
            console.print(f"[green]OK[/green] Deleted room {room_id}")
        except ReGaError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@room.command("add-device")
@click.argument("room_id", type=int)
@click.argument("channel_id", type=int)
def room_add_device(room_id: int, channel_id: int) -> None:
    """Add a device/channel to a room.

    ROOM_ID: The room's internal ID
    CHANNEL_ID: The channel's internal ID
    """
    with get_rega_client() as client:
        try:
            client.add_device_to_room(room_id, channel_id)
            console.print(f"[green]OK[/green] Added channel {channel_id} to room {room_id}")
        except ReGaError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@room.command("remove-device")
@click.argument("room_id", type=int)
@click.argument("channel_id", type=int)
def room_remove_device(room_id: int, channel_id: int) -> None:
    """Remove a device/channel from a room.

    ROOM_ID: The room's internal ID
    CHANNEL_ID: The channel's internal ID
    """
    with get_rega_client() as client:
        try:
            client.remove_device_from_room(room_id, channel_id)
            console.print(f"[green]OK[/green] Removed channel {channel_id} from room {room_id}")
        except ReGaError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@room.command("devices")
@click.argument("room_id", type=int)
def room_devices(room_id: int) -> None:
    """List devices/channels in a room.

    ROOM_ID: The room's internal ID
    """
    with get_rega_client() as client:
        try:
            devices = client.list_room_devices(room_id)

            if not devices:
                console.print("No devices in this room.")
                return

            table = Table(title=f"Devices in Room {room_id}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Address", style="yellow")

            for dev in devices:
                table.add_row(str(dev.id), dev.name, dev.address)

            console.print(table)
        except ReGaError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


# =============================================================================
# Link Commands
# =============================================================================


@main.group()
def link() -> None:
    """Manage device links (Direktverknüpfungen)."""
    pass


@link.command("list")
@click.option(
    "--address",
    "-a",
    help="Filter by device/channel address (e.g., 000B5D89B014D8:1)",
)
@click.option(
    "--interface",
    "-i",
    type=click.Choice(["HmIP-RF", "BidCos-RF"]),
    default="HmIP-RF",
    help="Interface to use (default: HmIP-RF)",
)
def link_list(address: str | None, interface: str) -> None:
    """List device links (Direktverknüpfungen)."""
    with get_backend() as backend:
        try:
            links = backend.list_links(address, interface)

            if not links:
                console.print("No links found.")
                return

            table = Table(title="Device Links")
            table.add_column("Sender", style="cyan")
            table.add_column("Receiver", style="green")
            table.add_column("Name", style="yellow")
            table.add_column("Description", style="magenta")

            for lnk in links:
                table.add_row(lnk.sender, lnk.receiver, lnk.name, lnk.description)

            console.print(table)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@link.command("get")
@click.argument("sender")
@click.argument("receiver")
@click.option(
    "--interface",
    "-i",
    type=click.Choice(["HmIP-RF", "BidCos-RF"]),
    default="HmIP-RF",
    help="Interface to use (default: HmIP-RF)",
)
def link_get(sender: str, receiver: str, interface: str) -> None:
    """Show link details.

    SENDER: Sender channel address
    RECEIVER: Receiver channel address
    """
    with get_backend() as backend:
        try:
            link_info = backend.get_link(sender, receiver, interface)

            if not link_info:
                error_console.print(f"[red]Link not found:[/red] {sender} -> {receiver}")
                sys.exit(1)

            table = Table(title=f"Link: {sender} -> {receiver}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Sender", link_info.sender)
            table.add_row("Receiver", link_info.receiver)
            table.add_row("Name", link_info.name or "(none)")
            table.add_row("Description", link_info.description or "(none)")
            table.add_row("Flags", str(link_info.flags))

            console.print(table)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@link.command("create")
@click.argument("sender")
@click.argument("receiver")
@click.option("--name", "-n", default="", help="Link name")
@click.option("--description", "-d", default="", help="Link description")
def link_create(sender: str, receiver: str, name: str, description: str) -> None:
    """Create a device link (Direktverknüpfung).

    SENDER: Sender channel address (e.g., 000B5D89B014D8:1)
    RECEIVER: Receiver channel address (e.g., 000E9569A23B4C:4)
    """
    with get_backend() as backend:
        try:
            backend.create_link(sender, receiver, name, description)
            console.print(f"[green]OK[/green] Created link: {sender} -> {receiver}")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@link.command("delete")
@click.argument("sender")
@click.argument("receiver")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def link_delete(sender: str, receiver: str, yes: bool) -> None:
    """Remove a device link.

    SENDER: Sender channel address
    RECEIVER: Receiver channel address
    """
    if not yes:
        if not click.confirm(f"Remove link {sender} -> {receiver}?"):
            console.print("Cancelled")
            return

    with get_backend() as backend:
        try:
            backend.delete_link(sender, receiver)
            console.print(f"[green]OK[/green] Removed link: {sender} -> {receiver}")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@link.group("config")
def link_config() -> None:
    """Manage link configuration (LINK paramset)."""
    pass


@link_config.command("get")
@click.argument("sender")
@click.argument("receiver")
@click.option(
    "--interface",
    "-i",
    type=click.Choice(["HmIP-RF", "BidCos-RF"]),
    default="HmIP-RF",
    help="Interface to use (default: HmIP-RF)",
)
def link_config_get(sender: str, receiver: str, interface: str) -> None:
    """Show link parameters (LINK paramset).

    SENDER: Sender channel address
    RECEIVER: Receiver channel address
    """
    with get_backend() as backend:
        try:
            params = backend.get_link_paramset(sender, receiver, interface)
            print_json(params)
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@link_config.command("set")
@click.argument("sender")
@click.argument("receiver")
@click.argument("params", nargs=-1, required=True)
@click.option(
    "--side",
    "-s",
    type=click.Choice(["sender", "receiver"]),
    default="receiver",
    help="Which side to set params on (default: receiver for actuator profiles)",
)
@click.option(
    "--interface",
    "-i",
    type=click.Choice(["HmIP-RF", "BidCos-RF"]),
    default="HmIP-RF",
    help="Interface to use (default: HmIP-RF)",
)
def link_config_set(
    sender: str, receiver: str, params: tuple[str, ...], side: str, interface: str
) -> None:
    """Set link parameters.

    SENDER: Sender channel address
    RECEIVER: Receiver channel address
    PARAMS: One or more key=value pairs (e.g., SHORT_DRIVING_MODE=1)

    By default sets on receiver side (actuator profiles like blind speed/timing).
    Use --side sender for button/switch profiles.

    Example: ccu link config set 000B5D:1 000E9A:4 SHORT_DRIVING_MODE=1
    """
    # Parse key=value pairs
    param_dict: dict[str, Any] = {}
    for param in params:
        if "=" not in param:
            error_console.print(
                f"[red]Error:[/red] Invalid parameter format: {param} (expected key=value)"
            )
            sys.exit(1)
        key, value_str = param.split("=", 1)

        # Parse value to appropriate type
        parsed_value: Any
        if value_str.lower() == "true":
            parsed_value = True
        elif value_str.lower() == "false":
            parsed_value = False
        else:
            try:
                parsed_value = int(value_str)
            except ValueError:
                try:
                    parsed_value = float(value_str)
                except ValueError:
                    parsed_value = value_str

        param_dict[key] = parsed_value

    with get_backend() as backend:
        try:
            backend.set_link_paramset(sender, receiver, param_dict, side, interface)
            side_label = "receiver (actuator)" if side == "receiver" else "sender (button)"
            console.print(f"[green]OK[/green] Updated {side_label} parameters: {sender} -> {receiver}")
            for key, value in param_dict.items():
                console.print(f"  {key} = {value}")
        except BackendError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
