"""Domain errors with precise HTTP mapping."""

from __future__ import annotations


class DomainError(Exception):
    """Base domain error for billing/metering failures."""


class EventConflictError(DomainError):
    """Same ``event_id`` reused with different billable content."""

    def __init__(self, event_id: str, detail: str = "event_id conflict"):
        """Initialize the conflict error.

        Args:
            event_id: Conflicting client-supplied event identifier.
            detail: Human-readable explanation for API clients.
        """
        self.event_id = event_id
        super().__init__(detail)


class InvoiceImmutableError(DomainError):
    """Raised when a caller attempts to mutate a finalized invoice."""

    def __init__(self, invoice_id: str, detail: str = "finalized invoice is immutable"):
        """Initialize the immutability error.

        Args:
            invoice_id: Invoice that cannot be rewritten.
            detail: Human-readable explanation.
        """
        self.invoice_id = invoice_id
        super().__init__(detail)


class CutoverBlockedError(DomainError):
    """Raised when shadow reconciliation forbids pricing cutover."""

    def __init__(self, detail: str = "pricing cutover blocked by unexpected deltas"):
        """Initialize the cutover block error.

        Args:
            detail: Human-readable explanation of why cutover failed.
        """
        super().__init__(detail)
