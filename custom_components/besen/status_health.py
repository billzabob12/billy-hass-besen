"""Distinguish fresh charge reports from metadata and heartbeat traffic."""

import time


class ChargeStatusHealth:
    """Track immutable charge objects separately from transport availability."""

    def __init__(self) -> None:
        self.received = time.monotonic()
        self.last_recovery = float("-inf")

    def observe_live(self, stamp: float | None) -> None:
        """Accept the timestamp of a decoded 0x04/0x0D live metering report."""
        if isinstance(stamp, (int, float)):
            self.received = max(self.received, stamp)

    @property
    def age(self) -> float:
        return time.monotonic() - self.received

    @property
    def fresh(self) -> bool:
        return self.age < 90

    def recover_due(self) -> bool:
        now = time.monotonic()
        if self.age < 90 or now - self.last_recovery < 180:
            return False
        self.last_recovery = now
        return True
