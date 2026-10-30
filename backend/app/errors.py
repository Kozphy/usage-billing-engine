"""Domain errors with precise HTTP mapping."""

from __future__ import annotations


class DomainError(Exception):
    """Base domain error."""


class EventConflictError(DomainError):
    """Same event_id reused with different billable content."""

    def __init__(self, event_id: str, detail: str = "event_id conflict"):
        self.event_id = event_id
        super().__init__(detail)


class InvoiceImmutableError(DomainError):
    def __init__(self, invoice_id: str, detail: str = "finalized invoice is immutable"):
        self.invoice_id = invoice_id
        super().__init__(detail)


class CutoverBlockedError(DomainError):
    def __init__(self, detail: str = "pricing cutover blocked by unexpected deltas"):
        super().__init__(detail)
