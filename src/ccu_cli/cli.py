"""CLI interface for ccu-cli."""

import sys
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from .client import CCUClient
from .config import load_config
from .rega import ReGaClient, ReGaError

console = Console()
error_console = Console(stderr=True)


def get_client() -> CCUClient:
    """Create a CCU client with loaded configuration."""
    config = load_config()
    return CCUClient(config)


def get_rega_client() -> ReGaClient:
    """Create a ReGa client with loaded configuration."""
    config = load_config()
    return ReGaClient(config)


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    import json

    console.print_json(json.dumps(data))


@click.group()
@click.version_option()
def main() -> None:
    """CLI tool for interacting with CCU-Jack on RaspberryMatic/CCU3."""
    pass


@main.command()
def info() -> None:
    """Show CCU-Jack server information."""
    with get_client() as client:
        try:
            data = client.get_vendor_info()
            print_json(data)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command()
def devices() -> None:
    """List all devices."""
    with get_client() as client:
        try:
            devices = client.list_devices()
            # Filter out navigation links
            devices = [d for d in devices if d.get("rel") == "device"]

            table = Table(title="Devices")
            table.add_column("Serial", style="cyan")
            table.add_column("Name", style="green")

            for device in devices:
                serial = device.get("href", "")
                name = device.get("title", "")
                table.add_row(serial, name)

            console.print(table)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command()
@click.argument("serial")
def device(serial: str) -> None:
    """Show device details."""
    with get_client() as client:
        try:
            data = client.get_device(serial)
            print_json(data)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command()
@click.argument("path")
def get(path: str) -> None:
    """Read a datapoint value.

    PATH format: <serial>/<channel>/<datapoint>
    Example: NEQ0123456/1/TEMPERATURE
    """
    try:
        parts = path.split("/")
        if len(parts) != 3:
            raise click.BadParameter("Path must be <serial>/<channel>/<datapoint>")
        serial, channel, datapoint = parts
        channel_int = int(channel)
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] Invalid path format: {e}")
        sys.exit(1)

    with get_client() as client:
        try:
            value = client.get_datapoint(serial, channel_int, datapoint)
            console.print(value)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command("set")
@click.argument("path")
@click.argument("value")
def set_value(path: str, value: str) -> None:
    """Set a datapoint value.

    PATH format: <serial>/<channel>/<datapoint>
    Example: ccu set NEQ0123456/1/STATE true
    """
    try:
        parts = path.split("/")
        if len(parts) != 3:
            raise click.BadParameter("Path must be <serial>/<channel>/<datapoint>")
        serial, channel, datapoint = parts
        channel_int = int(channel)
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

    with get_client() as client:
        try:
            client.set_datapoint(serial, channel_int, datapoint, parsed_value)
            console.print(f"[green]OK[/green] {path} = {parsed_value}")
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command()
def sysvars() -> None:
    """List all system variables."""
    with get_client() as client:
        try:
            sysvars = client.list_sysvars()
            # Filter out navigation links
            sysvars = [s for s in sysvars if s.get("rel") not in ("root", "collection")]

            table = Table(title="System Variables")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")

            for sysvar in sysvars:
                sysvar_id = sysvar.get("href", "")
                name = sysvar.get("title", "")
                table.add_row(sysvar_id, name)

            console.print(table)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command()
def programs() -> None:
    """List all programs."""
    with get_client() as client:
        try:
            programs = client.list_programs()
            # Filter out navigation links
            programs = [p for p in programs if p.get("rel") not in ("root", "collection")]

            table = Table(title="Programs")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")

            for program in programs:
                program_id = program.get("href", "")
                name = program.get("title", "")
                table.add_row(program_id, name)

            console.print(table)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command()
@click.argument("name")
def run(name: str) -> None:
    """Execute a program by name."""
    with get_client() as client:
        try:
            client.run_program(name)
            console.print(f"[green]OK[/green] Program '{name}' executed")
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command()
@click.argument("serial")
@click.argument("channel", type=int)
def config(serial: str, channel: int) -> None:
    """Show device/channel configuration (MASTER parameters)."""
    with get_client() as client:
        try:
            data = client.get_device_config(serial, channel)
            print_json(data)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@main.command()
def refresh() -> None:
    """Reload device data from CCU."""
    with get_client() as client:
        try:
            client.refresh()
            console.print("[green]OK[/green] CCU-Jack refreshed")
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


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

            for r in rooms:
                table.add_row(str(r["id"]), r["name"])

            console.print(table)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


@room.command("create")
@click.argument("name")
def room_create(name: str) -> None:
    """Create a new room."""
    with get_rega_client() as client:
        try:
            room_id = client.create_room(name)
            console.print(f"[green]OK[/green] Created room '{name}' with ID {room_id}")
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


if __name__ == "__main__":
    main()
