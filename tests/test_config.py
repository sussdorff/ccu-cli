"""Tests for configuration loading."""

import pytest
from ccu_cli.config import CCUConfig, load_config


class TestCCUConfig:
    """Tests for CCUConfig dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = CCUConfig()

        assert config.host == "localhost"
        assert config.https is False
        assert config.username is None
        assert config.password is None

    def test_auth_when_credentials_set(self):
        """Should return auth tuple when both credentials set."""
        config = CCUConfig(username="admin", password="secret")

        assert config.auth == ("admin", "secret")

    def test_auth_none_when_no_credentials(self):
        """Should return None when credentials not set."""
        config = CCUConfig()

        assert config.auth is None

    def test_auth_none_when_partial_credentials(self):
        """Should return None when only one credential set."""
        config_user_only = CCUConfig(username="admin")
        config_pass_only = CCUConfig(password="secret")

        assert config_user_only.auth is None
        assert config_pass_only.auth is None


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_loads_from_environment(self, monkeypatch):
        """Should load config from environment variables."""
        monkeypatch.setenv("CCU_HOST", "env-ccu.local")
        monkeypatch.setenv("CCU_HTTPS", "true")
        monkeypatch.setenv("CCU_USERNAME", "envuser")
        monkeypatch.setenv("CCU_PASSWORD", "envpass")

        config = load_config()

        assert config.host == "env-ccu.local"
        assert config.https is True
        assert config.username == "envuser"
        assert config.password == "envpass"

    def test_loads_from_toml(self, tmp_path, monkeypatch):
        """Should load config from XDG config file."""
        config_dir = tmp_path / "ccu-cli"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text("""
[ccu]
host = "toml-ccu.local"
https = true
username = "tomluser"
password = "tomlpass"
""")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        # Clear any env vars that might override
        monkeypatch.delenv("CCU_HOST", raising=False)
        monkeypatch.delenv("CCU_HTTPS", raising=False)
        monkeypatch.delenv("CCU_USERNAME", raising=False)
        monkeypatch.delenv("CCU_PASSWORD", raising=False)

        config = load_config()

        assert config.host == "toml-ccu.local"
        assert config.https is True
        assert config.username == "tomluser"
        assert config.password == "tomlpass"

    def test_env_overrides_toml(self, tmp_path, monkeypatch):
        """Environment variables should override TOML config."""
        config_dir = tmp_path / "ccu-cli"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text("""
[ccu]
host = "toml-ccu.local"
https = false
""")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.setenv("CCU_HOST", "env-override.local")

        config = load_config()

        assert config.host == "env-override.local"
        assert config.https is False  # From TOML
