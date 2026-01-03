"""Shared test fixtures."""

import pytest
import httpx
from httpx import MockTransport, Response

from ccu_cli.config import CCUConfig
from ccu_cli.client import CCUClient


@pytest.fixture
def config() -> CCUConfig:
    """Test configuration."""
    return CCUConfig(host="test-ccu", port=2121)


@pytest.fixture
def mock_transport_factory():
    """Factory for creating mock transports with custom handlers."""

    def factory(handler):
        return MockTransport(handler)

    return factory


@pytest.fixture
def mock_client(config, mock_transport_factory):
    """Factory for creating CCUClient with mocked transport."""

    def factory(handler):
        client = CCUClient(config)
        client._client = httpx.Client(
            base_url=config.base_url,
            transport=mock_transport_factory(handler),
        )
        return client

    return factory


# Sample response fixtures
@pytest.fixture
def devices_response() -> dict:
    """Sample /device endpoint response."""
    return {
        "identifier": "device",
        "title": "Devices",
        "~links": [
            {"rel": "root", "href": "..", "title": "Root"},
            {"rel": "device", "href": "NEQ0123456", "title": "Living Room Switch"},
            {"rel": "device", "href": "NEQ0789012", "title": "Kitchen Thermostat"},
        ],
    }


@pytest.fixture
def sysvars_response() -> dict:
    """Sample /sysvar endpoint response."""
    return {
        "identifier": "sysvar",
        "title": "System Variables",
        "~links": [
            {"rel": "root", "href": "..", "title": "Root"},
            {"rel": "sysvar", "href": "1234", "title": "Presence"},
            {"rel": "sysvar", "href": "5678", "title": "AlarmActive"},
        ],
    }


@pytest.fixture
def programs_response() -> dict:
    """Sample /program endpoint response."""
    return {
        "identifier": "program",
        "title": "Programs",
        "~links": [
            {"rel": "root", "href": "..", "title": "Root"},
            {"rel": "program", "href": "9001", "title": "All Lights Off"},
            {"rel": "program", "href": "9002", "title": "Good Night"},
        ],
    }
