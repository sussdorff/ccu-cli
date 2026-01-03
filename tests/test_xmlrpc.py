"""Tests for XMLRPCClient."""

from unittest.mock import MagicMock, patch
from xmlrpc.client import Fault

import pytest

from ccu_cli.config import CCUConfig
from ccu_cli.xmlrpc import DeviceLink, LinkInfo, XMLRPCClient, XMLRPCError


@pytest.fixture
def xmlrpc_config() -> CCUConfig:
    """Test configuration for XML-RPC client."""
    return CCUConfig(host="test-ccu", port=2121)


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

    def test_uses_https_when_configured(self):
        """Should use HTTPS when configured."""
        config = CCUConfig(host="test-ccu", https=True)
        client = XMLRPCClient(config)
        assert client.base_url.startswith("https://")

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


class TestGetLinkPeers:
    """Tests for XMLRPCClient.get_link_peers()."""

    def test_returns_peer_addresses(self, mock_xmlrpc_client, mock_proxy):
        """Should return list of peer addresses."""
        mock_proxy.getLinkPeers.return_value = [
            "0013A40997105E:4",
            "0013A409971044:4",
        ]

        client = mock_xmlrpc_client()
        peers = client.get_link_peers("000B5D89B014D8:1")

        mock_proxy.getLinkPeers.assert_called_once_with("000B5D89B014D8:1")
        assert len(peers) == 2
        assert "0013A40997105E:4" in peers

    def test_raises_on_error(self, mock_xmlrpc_client, mock_proxy):
        """Should raise XMLRPCError on failure."""
        mock_proxy.getLinkPeers.side_effect = Fault(1, "Unknown channel")

        client = mock_xmlrpc_client()

        with pytest.raises(XMLRPCError, match="Failed to get link peers"):
            client.get_link_peers("invalid")


class TestAddLink:
    """Tests for XMLRPCClient.add_link()."""

    def test_creates_link(self, mock_xmlrpc_client, mock_proxy):
        """Should create a device link."""
        mock_proxy.addLink.return_value = None

        client = mock_xmlrpc_client()
        client.add_link(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
            "Test Link",
            "Test Description",
        )

        mock_proxy.addLink.assert_called_once_with(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
            "Test Link",
            "Test Description",
        )

    def test_creates_link_without_name(self, mock_xmlrpc_client, mock_proxy):
        """Should create link with empty name and description."""
        mock_proxy.addLink.return_value = None

        client = mock_xmlrpc_client()
        client.add_link("000B5D89B014D8:1", "0013A40997105E:4")

        mock_proxy.addLink.assert_called_once_with(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
            "",
            "",
        )

    def test_raises_on_error(self, mock_xmlrpc_client, mock_proxy):
        """Should raise XMLRPCError on failure."""
        mock_proxy.addLink.side_effect = Fault(1, "Link already exists")

        client = mock_xmlrpc_client()

        with pytest.raises(XMLRPCError, match="Failed to add link"):
            client.add_link("a", "b")


class TestRemoveLink:
    """Tests for XMLRPCClient.remove_link()."""

    def test_removes_link(self, mock_xmlrpc_client, mock_proxy):
        """Should remove a device link."""
        mock_proxy.removeLink.return_value = None

        client = mock_xmlrpc_client()
        client.remove_link("000B5D89B014D8:1", "0013A40997105E:4")

        mock_proxy.removeLink.assert_called_once_with(
            "000B5D89B014D8:1",
            "0013A40997105E:4",
        )

    def test_raises_on_error(self, mock_xmlrpc_client, mock_proxy):
        """Should raise XMLRPCError on failure."""
        mock_proxy.removeLink.side_effect = Fault(1, "Link not found")

        client = mock_xmlrpc_client()

        with pytest.raises(XMLRPCError, match="Failed to remove link"):
            client.remove_link("a", "b")


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


class TestListDevices:
    """Tests for XMLRPCClient.list_devices()."""

    def test_returns_device_list(self, mock_xmlrpc_client, mock_proxy):
        """Should return list of devices."""
        mock_proxy.listDevices.return_value = [
            {"ADDRESS": "000B5D89B014D8", "TYPE": "HmIP-WRC6"},
            {"ADDRESS": "0013A40997105E", "TYPE": "HmIP-FBL"},
        ]

        client = mock_xmlrpc_client()
        devices = client.list_devices()

        assert len(devices) == 2
        assert devices[0]["TYPE"] == "HmIP-WRC6"


class TestGetDeviceDescription:
    """Tests for XMLRPCClient.get_device_description()."""

    def test_returns_device_description(self, mock_xmlrpc_client, mock_proxy):
        """Should return device description."""
        mock_proxy.getDeviceDescription.return_value = {
            "ADDRESS": "000B5D89B014D8",
            "TYPE": "HmIP-WRC6",
            "PARAMSETS": ["MASTER", "VALUES"],
        }

        client = mock_xmlrpc_client()
        desc = client.get_device_description("000B5D89B014D8")

        mock_proxy.getDeviceDescription.assert_called_once_with("000B5D89B014D8")
        assert desc["TYPE"] == "HmIP-WRC6"


class TestXMLRPCClientContextManager:
    """Tests for XMLRPCClient context manager."""

    def test_enters_and_exits(self, xmlrpc_config):
        """Should support context manager protocol."""
        client = XMLRPCClient(xmlrpc_config)

        with client as c:
            assert c is client
