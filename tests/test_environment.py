"""Tests for hermetic test environment configuration."""

import os
from pathlib import Path


def test_home_and_git_configuration_are_isolated():
    home = Path.home()

    assert home == Path(os.environ["HOME"])
    assert os.environ["XDG_CONFIG_HOME"] == str(home / ".config")
    assert os.environ["XDG_STATE_HOME"] == str(home / ".local" / "state")
    assert os.environ["XDG_CACHE_HOME"] == str(home / ".cache")
    assert os.environ["GIT_CONFIG_GLOBAL"] == os.devnull
    assert os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
