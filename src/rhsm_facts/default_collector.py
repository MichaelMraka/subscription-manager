# A facts collector that does what we need.
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

from rhsm_facts import hardware
from rhsm_facts import software
from rhsm_facts import custom


class DefaultCollector(object):
    def __init__(self,
                 custom_facts_dir=None):
        self.custom_facts_dir = custom_facts_dir

        # This is a list because the order matters.
        self.collectors = [hardware.Collector(),
                           software.Collector(),
                           custom.Collector(custom_facts_dir=self.custom_facts_dir)]
        self.facts = {}

    def collect(self, collected_facts=None):
        """Collect facts and add/update/filter the collected_facts dict.

        Note this does modify collected facts.
        """
        for collector in self.collectors:
            print "collector", collector
            fact_data = collector.collect(collected_facts=collected_facts)
            collected_facts.update(fact_data)

        return collected_facts
