"""Idempotent, atomic application of ledger events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class EventConflictError(ValueError):
    """An event id was reused with different content."""


class InsufficientBalanceError(ValueError):
    """A batch would make an account balance negative."""


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    account_id: str
    delta: int


class EventLedger:
    """In-memory ledger with retry-safe, all-or-nothing batches."""

    def __init__(self) -> None:
        self._balances: dict[str, int] = {}
        self._processed: dict[str, LedgerEvent] = {}

    def balance(self, account_id: str) -> int:
        return self._balances.get(account_id, 0)

    def apply_batch(self, events: Iterable[LedgerEvent]) -> None:
        staged_balances = self._balances.copy()
        staged_processed = self._processed.copy()
        for event in events:
            self._validate(event)
            previous = staged_processed.get(event.event_id)
            if previous is not None:
                if previous != event:
                    raise EventConflictError(f"conflicting event id: {event.event_id}")
                continue
            new_balance = staged_balances.get(event.account_id, 0) + event.delta
            if new_balance < 0:
                raise InsufficientBalanceError(event.account_id)
            staged_balances[event.account_id] = new_balance
            staged_processed[event.event_id] = event
        self._balances = staged_balances
        self._processed = staged_processed

    @staticmethod
    def _validate(event: LedgerEvent) -> None:
        if not event.event_id or not event.account_id:
            raise ValueError("event_id and account_id must be non-empty")
        if isinstance(event.delta, bool) or not isinstance(event.delta, int):
            raise TypeError("delta must be an integer")
