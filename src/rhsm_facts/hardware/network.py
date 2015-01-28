# Module to probe Hardware info from the system
#
# Copyright (c) 2010-2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import socket

from rhsm_facts import exceptions


class NetworkFactCollectorError(exceptions.FactCollectorError):
    pass


class SocketInfo(object):
    socket_family = socket.AF_INET

    def __init__(self, hostname=None):
        self.host = hostname or self.hostname()
        self.addrinfo = self._addrinfo()

    def _hostname(self):
        return socket.gethostname()

    def _addrinfo(self):
        return socket.getaddrinfo(self.host, None, self.socket_family, socket.SOCK_STREAM)


class Ipv6SocketInfo(SocketInfo):
    socket_family = socket.AF_INET6


class NetworkInfo(object):
    def __init__(self):
        self.host = self.hostname()
        self.ipv4 = SocketInfo(hostname=self.host)
        self.ipv6 = Ipv6SocketInfo(hostname=self.host)

        self.ipv4_address = self.ipv4_info()
        self.ipv6_address = self.ipv6_info()

    def hostname(self):
        return socket.gethostname()

    # Note: if something fails in here, we raise an NetworkFactCollectorError instead
    # of defaulting to '127.0.0.1'
    def ipv4_info(self):
        info = self.ipv4.addrinfo
        ip_list = set([x[4][0] for x in info])
        ipv4_address = ', '.join(ip_list)
        return ipv4_address

    def ipv6_info(self):
        info = self.ipv6.addrinfo
        ip_list = set([x[4][0] for x in info])
        ipv6_address = ', '.join(ip_list)
        return ipv6_address


class Network(object):
    def __init__(self, prefix=None, testing=None):
        self.data = {}
        self.prefix = prefix or ''

    def collect(self, collected_facts=None):
        netinfo = {}
        try:
            network_info = NetworkInfo()
        except Exception, e:
            raise NetworkFactCollectorError(e)

        netinfo['network.hostname'] = network_info.host
        netinfo['network.ipv4_address'] = network_info.ipv4_info()
        netinfo['network.ipv6_address'] = network_info.ipv6_info()

        self.data.update(netinfo)
        return self.data
