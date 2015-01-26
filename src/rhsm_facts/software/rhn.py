# Collect facts related to rhn setup.
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

import sys


class RhnClassicCheck(object):
    def is_registered_with_classic(self):
        """Check if system is currently registered to RHN "classic".

        Attempts to import rhn.up2date_client.up2dateAuth and checks
        for a valid RHN system id.

        Returns True if the system is registered to RHN."""
        try:
            sys.path.append('/usr/share/rhn')
            from up2date_client import up2dateAuth
        except ImportError:
            return False

        return up2dateAuth.getSystemId() is not None
