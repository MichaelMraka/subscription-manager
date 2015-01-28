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
    def __init__(self, info=None):
        super(NetworkFactCollectorError, self).__init__(collector='network')
        self.msg = "Error reading networking information"
        self.info = info


class SocketAddressInfo(object):
    def __init__(self):
        self.host = self.hostname()
        self.ipv4_address = self.ipv4_info(self.host)
        self.ipv6_address = self.ipv6_info(self.host)

    def hostname(self):
        return socket.gethostname()

    def ipv4_info(self, host):
        ipv4_address = None
        try:
            info = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
            ip_list = set([x[4][0] for x in info])
            ipv4_address = ', '.join(ip_list)
        except socket.error:
            ipv4_address = "127.0.0.1"

        return ipv4_address

    def ipv6_info(self, host):
        ipv6_address = None
        try:
            info = socket.getaddrinfo(host, None, socket.AF_INET6, socket.SOCK_STREAM)
            ip_list = set([x[4][0] for x in info])
            ipv6_address = ', '.join(ip_list)
        except socket.error:
            ipv6_address = "::1"

        return ipv6_address


class Network(object):
    def __init__(self, prefix=None, testing=None):
        self.data = {}
        self.prefix = prefix or ''

    def collect(self):
        netinfo = {}
        try:
            socket_info = SocketAddressInfo()
        except Exception, e:
            raise NetworkFactCollectorError(info="%s" % e)

        netinfo['network.hostname'] = socket_info.host
        netinfo['network.ipv4_address'] = socket.ipv4_address
        netinfo['network.ipv6_address'] = socket.ipv6_address

        self.data.update(netinfo)
        return self.data

