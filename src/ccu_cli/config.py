"""Configuration management with XDG support and .env fallback."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

try:
    import tomllib
except ImportError:
    import tomli as tomllib


class ConfigurationError(Exception):
    """Error in configuration."""

    pass


@dataclass
class CCUConfig:
    """CCU connection configuration."""

    host: str = "localhost"
    https: bool = False
    username: str | None = None
    password: str | None = None

    @property
    def auth(self) -> tuple[str, str] | None:
        """Return auth tuple if credentials are configured."""
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def validate(self) -> None:
        """Validate that all required configuration is present.

        Raises:
            ConfigurationError: If required configuration is missing
        """
        missing = []
        if not self.host or self.host == "localhost":
            missing.append("CCU_HOST")
        if not self.username:
            missing.append("CCU_USERNAME")
        if not self.password:
            missing.append("CCU_PASSWORD")

        if missing:
            raise ConfigurationError(
                f"Missing required configuration: {', '.join(missing)}. "
                "Set these in .env file or environment variables."
            )


def get_xdg_config_home() -> Path:
    """Get XDG_CONFIG_HOME or default to ~/.config."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def load_config() -> CCUConfig:
    """Load configuration from XDG config, environment, and .env file.

    Priority (later overrides earlier):
    1. XDG config file
    2. Environment variables
    3. Local .env file
    """
    config = CCUConfig()

    # 1. Load from XDG config file
    xdg_config_file = get_xdg_config_home() / "ccu-cli" / "config.toml"
    if xdg_config_file.exists():
        with open(xdg_config_file, "rb") as f:
            toml_config = tomllib.load(f)
            ccu_section = toml_config.get("ccu", {})
            if "host" in ccu_section:
                config.host = ccu_section["host"]
            if "https" in ccu_section:
                config.https = ccu_section["https"]
            if "username" in ccu_section:
                config.username = ccu_section["username"]
            if "password" in ccu_section:
                config.password = ccu_section["password"]

    # 2. Load from environment variables (may be set before or after .env)
    # We load .env first so environment variables can override .env
    load_dotenv()  # Load .env file if present

    # 3. Apply environment variables (includes .env values now)
    if env_host := os.environ.get("CCU_HOST"):
        config.host = env_host
    if env_https := os.environ.get("CCU_HTTPS"):
        config.https = env_https.lower() in ("true", "1", "yes")
    if env_username := os.environ.get("CCU_USERNAME"):
        config.username = env_username
    if env_password := os.environ.get("CCU_PASSWORD"):
        config.password = env_password

    return config
