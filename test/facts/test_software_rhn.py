import unittest

from rhsm_facts.software import rhn


class RhnClassicCheckTest(unittest.TestCase):
    def test_without_perms(self):
        # for unit tests, we don't have perms to read the
        # system id, so this should always be false.
        rcc = rhn.RhnClassicCheck()
        registered = rcc.is_registered_with_classic()
        self.assertFalse(registered)
