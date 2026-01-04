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

```bash
# Show CCU info
ccu info

# List all devices
ccu devices

# Show device details
ccu device <address>

# Read a datapoint
ccu get <address>:<channel>/<datapoint>

# Set a datapoint
ccu set <address>:<channel>/<datapoint> <value>

# List system variables
ccu sysvars

# List programs
ccu program list

# Show program details
ccu program show <id-or-name>

# Run a program
ccu program run <id-or-name>

# Enable/disable a program
ccu program enable <id-or-name>
ccu program disable <id-or-name>

# List rooms
ccu rooms

# Manage rooms
ccu room create <name>
ccu room rename <id> <new-name>
ccu room delete <id>
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
