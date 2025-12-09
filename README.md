# ccu-cli

CLI tool for interacting with [CCU-Jack](https://github.com/mdzio/ccu-jack) on RaspberryMatic/CCU3.

## Prerequisites

### CCU-Jack Installation on RaspberryMatic

1. Download the latest addon from [CCU-Jack Releases](https://github.com/mdzio/ccu-jack/releases)
   - File: `ccu-jack-ccu-addon-x.x.x.tar.gz`

2. Install via RaspberryMatic Web UI:
   - Navigate to: **Einstellungen** > **Systemsteuerung** > **Zusatzsoftware**
   - Click **Durchsuchen** and select the downloaded `.tar.gz` file
   - Click **Installieren**

3. After installation, CCU-Jack runs on:
   - HTTP: `http://<ccu-ip>:2121`
   - HTTPS: `https://<ccu-ip>:2122`

4. Verify installation:
   ```bash
   curl -s "http://<ccu-ip>:2121/~vendor" | jq
   ```

### CCU-Jack Configuration (Optional)

Access the CCU-Jack web UI at `http://<ccu-ip>:2121` to:
- Configure authentication (recommended for security)
- Enable/disable MQTT server
- Set up virtual devices

## Installation

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/<user>/ccu-cli.git
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
port = 2121
https = false

# Optional authentication
# username = "admin"
# password = "secret"
```

### Environment variables

```bash
export CCU_HOST="raspberrymatic.local"
export CCU_PORT="2121"
export CCU_USERNAME="admin"
export CCU_PASSWORD="secret"
```

### Local `.env` file (development)

For local development, create a `.env` file in the project root:

```bash
CCU_HOST=raspberrymatic.local
CCU_PORT=2121
CCU_USERNAME=admin
CCU_PASSWORD=secret
```

## Usage

```bash
# List all devices
ccu devices

# Show device details
ccu device <serial>

# Read a datapoint
ccu get <serial>/<channel>/<datapoint>

# Set a datapoint
ccu set <serial>/<channel>/<datapoint> <value>

# List system variables
ccu sysvars

# List programs
ccu programs

# Execute a program
ccu run <program-name>
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

## Documentation

CCU-Jack documentation is included as a git submodule in `docs/ccu-jack/`.

- [CCU-Jack Wiki](https://github.com/mdzio/ccu-jack/wiki)
- [REST API (VEAP)](https://github.com/mdzio/ccu-jack/wiki/VEAP-Dienste)
- [CURL Examples](https://github.com/mdzio/ccu-jack/wiki/CURL)

## License

MIT
