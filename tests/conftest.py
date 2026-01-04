"""Shared test fixtures."""

import pytest
import httpx
from httpx import MockTransport, Response

from ccu_cli.config import CCUConfig
from ccu_cli.rega import ReGaClient


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
