import pytest

from src.event_ledger import (
    EventConflictError,
    EventLedger,
    InsufficientBalanceError,
    LedgerEvent,
)


def test_applies_batch_to_multiple_accounts():
    ledger = EventLedger()
    ledger.apply_batch(
        [
            LedgerEvent("e1", "alice", 10),
            LedgerEvent("e2", "bob", 7),
        ]
    )
    assert ledger.balance("alice") == 10
    assert ledger.balance("bob") == 7


def test_retry_of_identical_event_is_idempotent():
    ledger = EventLedger()
    event = LedgerEvent("e1", "alice", 10)
    ledger.apply_batch([event])
    ledger.apply_batch([event])
    assert ledger.balance("alice") == 10


def test_duplicate_inside_one_batch_is_idempotent():
    ledger = EventLedger()
    event = LedgerEvent("e1", "alice", 10)
    ledger.apply_batch([event, event])
    assert ledger.balance("alice") == 10


def test_reused_id_with_different_content_is_rejected():
    ledger = EventLedger()
    ledger.apply_batch([LedgerEvent("e1", "alice", 10)])
    with pytest.raises(EventConflictError):
        ledger.apply_batch([LedgerEvent("e1", "alice", 20)])
    assert ledger.balance("alice") == 10


def test_failed_batch_has_no_partial_effects_and_can_retry():
    ledger = EventLedger()
    bad_batch = [
        LedgerEvent("credit", "alice", 10),
        LedgerEvent("overdraft", "bob", -1),
    ]
    with pytest.raises(InsufficientBalanceError):
        ledger.apply_batch(bad_batch)
    assert ledger.balance("alice") == 0

    ledger.apply_batch([LedgerEvent("credit", "alice", 10)])
    assert ledger.balance("alice") == 10


@pytest.mark.parametrize(
    "event, error",
    [
        (LedgerEvent("", "alice", 1), ValueError),
        (LedgerEvent("e1", "", 1), ValueError),
        (LedgerEvent("e1", "alice", 1.5), TypeError),
        (LedgerEvent("e1", "alice", True), TypeError),
    ],
)
def test_invalid_events_do_not_mutate_state(event, error):
    ledger = EventLedger()
    with pytest.raises(error):
        ledger.apply_batch([event])
    assert ledger.balance("alice") == 0
