"""Tests for XMLRPCClient."""

from unittest.mock import MagicMock, patch
from xmlrpc.client import Fault

import pytest

from ccu_cli.config import CCUConfig
from ccu_cli.xmlrpc import DeviceLink, LinkInfo, XMLRPCClient, XMLRPCError


@pytest.fixture
def xmlrpc_config() -> CCUConfig:
    """Test configuration for XML-RPC client."""
    return CCUConfig(host="test-ccu")


@pytest.fixture
def mock_proxy():
    """Create a mock XML-RPC proxy."""
    return MagicMock()


@pytest.fixture
def mock_xmlrpc_client(xmlrpc_config, mock_proxy):
    """Factory for creating XMLRPCClient with mocked proxy."""

    def factory(interface: str = "HmIP-RF"):
        client = XMLRPCClient(xmlrpc_config, interface)
        client._proxy = mock_proxy
        return client

    return factory


class TestXMLRPCClientInit:
    """Tests for XMLRPCClient initialization."""

    def test_uses_hmip_port_by_default(self, xmlrpc_config):
        """Should use HmIP-RF port 2010 by default."""
        client = XMLRPCClient(xmlrpc_config)
        assert client.port == 2010

    def test_uses_bidcos_port_when_specified(self, xmlrpc_config):
        """Should use BidCos-RF port 2001 when specified."""
        client = XMLRPCClient(xmlrpc_config, interface="BidCos-RF")
        assert client.port == 2001

    def test_uses_http_by_default(self, xmlrpc_config):
        """Should use HTTP by default."""
        client = XMLRPCClient(xmlrpc_config)
        assert client.base_url.startswith("http://")

    def test_always_uses_http_for_xmlrpc(self):
        """Should always use HTTP for XML-RPC regardless of https config.

        The CCU XML-RPC API (ports 2001, 2010) uses plain HTTP.
        The https setting only applies to the web interface.
        """
        config = CCUConfig(host="test-ccu", https=True)
        client = XMLRPCClient(config)
        assert client.base_url.startswith("http://")

    def test_base_url_includes_port(self, xmlrpc_config):
        """Should include port in base URL."""
        client = XMLRPCClient(xmlrpc_config)
        assert ":2010" in client.base_url


class TestGetLinks:
    """Tests for XMLRPCClient.get_links()."""

    def test_returns_all_links(self, mock_xmlrpc_client, mock_proxy):
        """Should return all links when no address specified."""
        mock_proxy.getLinks.return_value = [
            {
                "SENDER": "000B5D89B014D8:1",
                "RECEIVER": "0013A40997105E:4",
                "NAME": "Test Link",
                "DESCRIPTION": "Test Description",
            },
            {
                "SENDER": "000B5D89B014D8:2",
                "RECEIVER": "0013A409971044:4",
                "NAME": "Another Link",
                "DESCRIPTION": "",
            },
        ]

        client = mock_xmlrpc_client()
        links = client.get_links()

        mock_proxy.getLinks.assert_called_once_with("", 0)
        assert len(links) == 2
        assert links[0] == DeviceLink(
            sender="000B5D89B014D8:1",
            receiver="0013A40997105E:4",
            name="Test Link",
            description="Test Description",
        )

    def test_filters_by_address(self, mock_xmlrpc_client, mock_proxy):
        """Should filter links by address when specified."""
        mock_proxy.getLinks.return_value = []

        client = mock_xmlrpc_client()
        client.get_links("000B5D89B014D8:1")

        mock_proxy.getLinks.assert_called_once_with("000B5D89B014D8:1", 0)

    def test_raises_on_error(self, mock_xmlrpc_client, mock_proxy):
        """Should raise XMLRPCError on failure."""
        mock_proxy.getLinks.side_effect = Fault(1, "Unknown device")

        client = mock_xmlrpc_client()

        with pytest.raises(XMLRPCError, match="Failed to get links"):
            client.get_links()


class TestGetLinkInfo:
    """Tests for XMLRPCClient.get_link_info()."""

    def test_returns_link_info(self, mock_xmlrpc_client, mock_proxy):
        """Should return link details."""
        mock_proxy.getLinkInfo.return_value = {
            "SENDER": "000B5D89B014D8:1",
            "RECEIVER": "0013A40997105E:4",
            "NAME": "Test Link",
            "DESCRIPTION": "Test Description",
            "FLAGS": 1,
        }

        client = mock_xmlrpc_client()
        info = client.get_link_info("000B5D89B014D8:1", "0013A40997105E:4")

        assert info is not None
        assert info.sender == "000B5D89B014D8:1"
        assert info.receiver == "0013A40997105E:4"
        assert info.name == "Test Link"
        assert info.flags == 1

    def test_returns_none_for_unknown_link(self, mock_xmlrpc_client, mock_proxy):
        """Should return None when link not found."""
        mock_proxy.getLinkInfo.side_effect = Fault(1, "Unknown Link")

        client = mock_xmlrpc_client()
        info = client.get_link_info("a", "b")

        assert info is None


class TestGetLinkParamset:
    """Tests for XMLRPCClient.get_link_paramset()."""

    def test_returns_paramset(self, mock_xmlrpc_client, mock_proxy):
        """Should return link paramset."""
        mock_proxy.getParamset.return_value = {
            "LONG_PRESS_TIME": 0.5,
            "DBL_PRESS_TIME": 0.3,
        }

        client = mock_xmlrpc_client()
        params = client.get_link_paramset("000B5D89B014D8:1", "0013A40997105E:4")

        mock_proxy.getParamset.assert_called_once_with(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
        )
        assert params["LONG_PRESS_TIME"] == 0.5

    def test_raises_on_error(self, mock_xmlrpc_client, mock_proxy):
        """Should raise XMLRPCError on failure."""
        mock_proxy.getParamset.side_effect = Fault(1, "Error")

        client = mock_xmlrpc_client()

        with pytest.raises(XMLRPCError, match="Failed to get link paramset"):
            client.get_link_paramset("a", "b")


class TestSetLinkParamset:
    """Tests for XMLRPCClient.set_link_paramset()."""

    def test_sets_paramset(self, mock_xmlrpc_client, mock_proxy):
        """Should set link paramset."""
        mock_proxy.putParamset.return_value = None

        client = mock_xmlrpc_client()
        client.set_link_paramset(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
            {"LONG_PRESS_TIME": 1.0},
        )

        mock_proxy.putParamset.assert_called_once_with(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
            {"LONG_PRESS_TIME": 1.0},
        )

    def test_raises_on_error(self, mock_xmlrpc_client, mock_proxy):
        """Should raise XMLRPCError on failure."""
        mock_proxy.putParamset.side_effect = Fault(1, "Error")

        client = mock_xmlrpc_client()

        with pytest.raises(XMLRPCError, match="Failed to set link paramset"):
            client.set_link_paramset("a", "b", {})


class TestAddLink:
    """Tests for XMLRPCClient.add_link()."""

    def test_creates_link(self, mock_xmlrpc_client, mock_proxy):
        """Should call addLink with correct arguments."""
        mock_proxy.addLink.return_value = None

        client = mock_xmlrpc_client("BidCos-RF")
        client.add_link("JEQ0263339:1", "REQ0666524:1", "Test", "Desc")

        mock_proxy.addLink.assert_called_once_with(
            "JEQ0263339:1", "REQ0666524:1", "Test", "Desc"
        )

    def test_creates_link_without_name(self, mock_xmlrpc_client, mock_proxy):
        """Should create link with empty name and description."""
        mock_proxy.addLink.return_value = None

        client = mock_xmlrpc_client()
        client.add_link("SENDER:1", "RECEIVER:1")

        mock_proxy.addLink.assert_called_once_with(
            "SENDER:1", "RECEIVER:1", "", ""
        )

    def test_raises_on_error(self, mock_xmlrpc_client, mock_proxy):
        """Should raise XMLRPCError on failure."""
        mock_proxy.addLink.side_effect = Fault(1, "Unknown device")

        client = mock_xmlrpc_client()

        with pytest.raises(XMLRPCError, match="Failed to create link"):
            client.add_link("a:1", "b:1")


class TestRemoveLink:
    """Tests for XMLRPCClient.remove_link()."""

    def test_removes_link(self, mock_xmlrpc_client, mock_proxy):
        """Should call removeLink with correct arguments."""
        mock_proxy.removeLink.return_value = None

        client = mock_xmlrpc_client("BidCos-RF")
        client.remove_link("JEQ0263339:1", "REQ0666524:1")

        mock_proxy.removeLink.assert_called_once_with(
            "JEQ0263339:1", "REQ0666524:1"
        )

    def test_raises_on_error(self, mock_xmlrpc_client, mock_proxy):
        """Should raise XMLRPCError on failure."""
        mock_proxy.removeLink.side_effect = Fault(1, "Unknown Link")

        client = mock_xmlrpc_client()

        with pytest.raises(XMLRPCError, match="Failed to remove link"):
            client.remove_link("a:1", "b:1")


class TestXMLRPCClientContextManager:
    """Tests for XMLRPCClient context manager."""

    def test_enters_and_exits(self, xmlrpc_config):
        """Should support context manager protocol."""
        client = XMLRPCClient(xmlrpc_config)

        with client as c:
            assert c is client
