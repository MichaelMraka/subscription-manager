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
import glob
import logging
import os

from rhsm import ourjson as json

log = logging.getLogger('rhsm-app.' + __name__)


class CustomCollector(object):
    def __init__(self, custom_facts_dir=None):
        self.custom_facts_dir = custom_facts_dir or '/etc/rhsm/facts/'
        self.facts = {}

    def collect(self, collected_facts=None):
        json_facts = self._load_custom_facts()
        collected_facts.update(json_facts)
        return collected_facts

    def _parse_facts_json(self, json_buffer, file_path):
        custom_facts = None

        try:
            custom_facts = json.loads(json_buffer)
        except ValueError:
            log.warn("Unable to load custom facts file: %s" % file_path)

        return custom_facts

    def _open_custom_facts(self, file_path):
        if not os.access(file_path, os.R_OK):
            log.warn("Unable to access custom facts file: %s" % file_path)
            return None

        try:
            f = open(file_path)
        except IOError:
            log.warn("Unabled to open custom facts file: %s" % file_path)
            return None

        json_buffer = f.read()
        f.close()

        return json_buffer

    def _load_custom_facts(self):
        """
        Load custom facts from .facts files in /etc/rhsm/facts.
        """
        # BZ 1112326 don't double the '/'
        facts_file_glob = "%s/facts/*.facts" % self.custom_facts_dir
        file_facts = {}
        for file_path in glob.glob(facts_file_glob):
            log.info("Loading custom facts from: %s" % file_path)
            json_buffer = self._open_custom_facts(file_path)

            if json_buffer is None:
                continue

            custom_facts = self._parse_facts_json(json_buffer, file_path)

            if custom_facts:
                file_facts.update(custom_facts)

        return file_facts
