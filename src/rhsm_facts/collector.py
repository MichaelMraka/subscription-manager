#
# Copyright (c) 2011-2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


class Collector(object):
    def __init__(self, collected_facts=None):
        # Each collector sends the already collected facts, so
        # we can reference other facts or modify.
        self.collected_facts = collected_facts or {}
        self.facts = {}

    def get_facts(self):
        """Return a dict of facts.

        key is a string, of form 'cpu.cpu_circuits'
        value is a string value.

        {'cpu.cpu_circuits': 'alot',
         'devices.smell': 'Acme Labs SmellBlaster 32FX!'}"""
        return self.facts
