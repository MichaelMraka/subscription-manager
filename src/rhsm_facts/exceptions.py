

class FactError(Exception):
    """Base class of errors that rhsm_facts may raise."""
    pass


class FactCollectorError(FactError):
    """Base class of errors that rhsm fact collector modules may raise."""
    pass
