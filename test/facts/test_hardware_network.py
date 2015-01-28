
import unittest
import mock
import socket

from rhsm_facts.hardware import network
from rhsm_facts import exceptions


class NetworkFactTest(unittest.TestCase):
    def test(self):
        nw = network.Network()
        info = nw.collect()
        self._verify_keys(info)

    def _verify_keys(self, info):
        self.assertTrue('network.ipv4_address' in info)
        self.assertTrue('network.ipv6_address' in info)
        self.assertTrue('network.hostname' in info)
        self.assertFalse('network.hostname' == 'localhost')
        self.assertFalse('network.ipv6_address' == '127.0.0.1')

    @mock.patch("rhsm_facts.hardware.network.SocketInfo",
               side_effect=socket.error)
    def test_socket_error(self, mock_socket_info):
        nw = network.Network()
        self.assertRaises(network.NetworkFactCollectorError, nw.collect)
        self.assertRaises(exceptions.FactError, nw.collect)

    @mock.patch("socket.getaddrinfo",
               return_value=[])
    def test_no_sockaddrinfos(self, mock_socket_getaddr):
        nw = network.Network()
        info = nw.collect()
        self._verify_keys(info)

    @mock.patch("rhsm_facts.hardware.network.Ipv6SocketInfo")
    @mock.patch("rhsm_facts.hardware.network.SocketInfo")
    def test_network_info(self, mock_socket_info, mock_ipv6_socket_info):
        mock_socket_info.addrinfo = [(2, 31, 6, '', ('82.94.164.162', 80, 2344))]
        mock_ipv6_socket_info.addrinfo = [(10, 1, 6, '', ('2001:888:2000:d::a2', 80, 0, 0))]
        nw = network.Network()
        info = nw.collect()
        self._verify_keys(info)

    @mock.patch("rhsm_facts.hardware.network.SocketInfo")
    def test_network_info_weird(self, mock_socket_info):
        mock_instance = mock_socket_info.return_value
        mock_instance.addrinfo = [(2, 31, 6, '')]

        # mock_socket_v6.addrinfo = [(10, 1, 6, '', ('2001:888:2000:d::a2', 80, 0, 0))]
        nw = network.Network()
        self.assertRaises(network.NetworkFactCollectorError, nw.collect)

    @mock.patch("rhsm_facts.hardware.network.NetworkInfo.hostname",
                return_value="234534tsdfg8ns7udf98gs7ndfg98s7ndfg98sdf7g8sdfg")
    def test_network_info_also_weird(self, mock_socket_info):
        mock_socket_info.addrinfo = [(2, 31, 6, '', ('82.94.164.162', 80, 2344))]

        # mock_socket_v6.addrinfo = [(10, 1, 6, '', ('2001:888:2000:d::a2', 80, 0, 0))]
        nw = network.Network()
        self.assertRaises(network.NetworkFactCollectorError, nw.collect)

    # test
    # multiple ips for a hostname
    # multiple interaces
