"""Distinguish fresh charge reports from metadata and heartbeat traffic."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from besen.models import BesenData, ChargeStatus


class ChargeStatusHealth:
    """Track immutable charge objects separately from transport availability."""

    def __init__(self, charge: ChargeStatus) -> None:
        self.charge = charge
        self.received = time.monotonic()
        self.last_recovery = float("-inf")

    def observe(self, data: BesenData) -> None:
        changed = data.charge is not self.charge
        self.charge = data.charge
        if changed and data.available and data.authenticated:
            self.received = time.monotonic()

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
