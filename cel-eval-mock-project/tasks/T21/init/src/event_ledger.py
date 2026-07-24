"""Buggy event ledger used by task T21."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class EventConflictError(ValueError):
    pass


class InsufficientBalanceError(ValueError):
    pass


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    account_id: str
    delta: int


class EventLedger:
    def __init__(self) -> None:
        self._balances: dict[str, int] = {}
        self._processed: set[str] = set()

    def balance(self, account_id: str) -> int:
        return self._balances.get(account_id, 0)

    def apply_batch(self, events: Iterable[LedgerEvent]) -> None:
        # Defects: a reused id is silently accepted, validation is incomplete,
        # and earlier events remain committed when a later event fails.
        for event in events:
            if event.event_id in self._processed:
                continue
            new_balance = self.balance(event.account_id) + event.delta
            if new_balance < 0:
                raise InsufficientBalanceError(event.account_id)
            self._balances[event.account_id] = new_balance
            self._processed.add(event.event_id)
