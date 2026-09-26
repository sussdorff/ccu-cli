"""Shared test fixtures."""

import os
from pathlib import Path

import pytest
from httpx import MockTransport

from ccu_cli.config import CCUConfig


@pytest.fixture(autouse=True)
def _isolated_environment(tmp_path_factory, monkeypatch):
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    # load_dotenv() searches upward from the package and writes os.environ
    # directly, so a .env beyond the worktree would leak into every test.
    monkeypatch.setattr("ccu_cli.config.load_dotenv", lambda *args, **kwargs: False)
    for name in ("CCU_HOST", "CCU_HTTPS", "CCU_USERNAME", "CCU_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def config() -> CCUConfig:
    """Test configuration."""
    return CCUConfig(host="test-ccu")


@pytest.fixture
def mock_transport_factory():
    """Factory for creating mock transports with custom handlers."""

    def factory(handler):
        return MockTransport(handler)

    return factory
