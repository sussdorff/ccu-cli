# ccu-cli

CLI tool for interacting with RaspberryMatic/CCU3 via [aiohomematic](https://github.com/danielperna84/hahomematic).

## Installation

```bash
# Clone repository
git clone https://github.com/<user>/ccu-cli.git
cd ccu-cli

# Install with uv
uv sync

# Or install globally
uv tool install .
```

## Configuration

Configuration is loaded in the following order (later sources override earlier):

1. XDG config: `$XDG_CONFIG_HOME/ccu-cli/config.toml` (default: `~/.config/ccu-cli/config.toml`)
2. Environment variables
3. Local `.env` file (for development)

### Config file (`~/.config/ccu-cli/config.toml`)

```toml
[ccu]
host = "raspberrymatic.local"
https = false

# Optional authentication
# username = "admin"
# password = "secret"
```

### Environment variables

```bash
export CCU_HOST="raspberrymatic.local"
export CCU_HTTPS="false"
export CCU_USERNAME="admin"
export CCU_PASSWORD="secret"
```

### Local `.env` file (development)

For local development, create a `.env` file in the project root:

```bash
CCU_HOST=raspberrymatic.local
CCU_USERNAME=admin
CCU_PASSWORD=secret
```

## Usage

The CLI follows a kubectl-style `resource action` pattern.

### Device Management

```bash
# List all devices
ccu device list

# Show device details
ccu device get <address>

# Rename a channel
ccu device rename <channel-id> <new-name>

# Show channel configuration (MASTER paramset)
ccu device config <address>:<channel>

# Refresh hub data (programs, sysvars) from CCU
ccu device refresh
```

### Datapoints

```bash
# Read a datapoint value
ccu datapoint get <address>:<channel>/<datapoint>

# Set a datapoint value
ccu datapoint set <address>:<channel>/<datapoint> <value>
```

### System Variables

```bash
# List system variables
ccu sysvar list
```

### Programs

```bash
# List programs
ccu program list

# Show program details
ccu program get <id-or-name>

# Run a program
ccu program run <id-or-name>

# Enable/disable a program
ccu program enable <id-or-name>
ccu program disable <id-or-name>

# Delete a program
ccu program delete <id-or-name> [--yes]
```

### Rooms

```bash
# List rooms
ccu room list

# Show room details and devices
ccu room get <room-id>

# Create a room
ccu room create <name>

# Rename a room
ccu room rename <room-id> <new-name>

# Delete a room
ccu room delete <room-id> [--yes]

# Manage devices in rooms
ccu room add-device <room-id> <channel-id>
ccu room remove-device <room-id> <channel-id>
ccu room devices <room-id>
```

### Device Links (Direktverknüpfungen)

```bash
# List all links (optionally filter by address)
ccu link list [-a <address>]

# Show link details
ccu link get <sender> <receiver>

# Create a link
ccu link create <sender> <receiver> [--name "Link Name"]

# Delete a link
ccu link delete <sender> <receiver> [--yes]

# Get link parameters (queries both sender and receiver sides)
ccu link config get <sender> <receiver>

# Set link parameters (default: receiver/actuator side)
ccu link config set <sender> <receiver> PARAM=value [PARAM2=value2 ...]

# Set parameters on sender/button side
ccu link config set --side sender <sender> <receiver> PARAM=value
```

### Thermostat Schedules (Wochenprogramme)

Manage heating profiles for HomeMatic thermostats (HM-TC-IT-WM-W-EU, HM-CC-RT-DN).

```bash
# Show current heating schedule
ccu schedule get <address>
ccu schedule get <address> --day mon
ccu schedule get <address> --profile 2

# Set a simple schedule (one heating period per day)
ccu schedule set-simple <address> --start 05:00 --end 22:00
ccu schedule set-simple <address> --start 06:00 --end 20:00 --comfort 21 --lowering 17
ccu schedule set-simple <address> --start 05:00 --end 22:00 --day mon --day tue --day wed

# Set constant temperature (no night setback)
ccu schedule set-constant <address> --temp 21
ccu schedule set-constant <address> --temp 21 --day sat --day sun

# Activate a specific profile (P1, P2, or P3)
ccu schedule activate <address> 1
```

**Schedule structure:**
- Each thermostat has 3 profiles (P1, P2, P3)
- Each profile has up to 13 time slots per day
- `WEEK_PROGRAM_POINTER` determines the active profile (0=P1, 1=P2, 2=P3)

### Other Commands

```bash
# Show CCU info
ccu info
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run CLI directly
uv run ccu --help
```

## License

MIT
