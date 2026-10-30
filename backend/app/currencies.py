"""ISO 4217 minor-unit exponents for invoice rounding and provider charges.

Exponents follow the ISO 4217 minor-unit scale (SIX Group List One), not
processor overrides. In particular TWD has 2 decimal places, ISK and CLP have
0, and IDR, CVE, and HUF have 2. Codes with no defined exponent (XAU, XAG,
XPT, XPD, XDR) are omitted and rejected.

The largest exponent in this table is 4, which fits ``Numeric(20, 4)`` storage.
"""

from __future__ import annotations


class UnknownCurrencyError(ValueError):
    """Currency is not an ISO 4217 code with a defined minor-unit exponent."""

    def __init__(self, currency: object) -> None:
        self.currency = currency
        super().__init__(
            "unknown currency "
            f"{currency!r}; expected an ISO 4217 code with a defined minor-unit exponent"
        )


# Built once so lookups do not rebuild the map per call.
_EXPONENT_0 = (
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG", "RWF", "UGX", "VND",
    "VUV", "XAF", "XOF", "XPF",
)
_EXPONENT_3 = (
    "BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND",
)
_EXPONENT_4 = (
    "CLF", "UYW",
)
_EXPONENT_2 = (
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN", "BAM", "BBD",
    "BDT", "BGN", "BMD", "BND", "BOB", "BRL", "BSD", "BTN", "BWP", "BYN", "BZD", "CAD",
    "CDF", "CHF", "CNY", "COP", "CRC", "CUP", "CVE", "CZK", "DKK", "DOP", "DZD", "EGP",
    "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP", "GMD", "GTQ", "GYD",
    "HKD", "HNL", "HTG", "HUF", "IDR", "ILS", "INR", "IRR", "JMD", "KES", "KGS", "KHR",
    "KPW", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", "MAD", "MDL", "MGA", "MKD",
    "MMK", "MNT", "MOP", "MRU", "MUR", "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN",
    "NIO", "NOK", "NPR", "NZD", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "QAR", "RON",
    "RSD", "RUB", "SAR", "SBD", "SCR", "SDG", "SEK", "SGD", "SHP", "SLE", "SOS", "SRD",
    "SSP", "STN", "SVC", "SYP", "SZL", "THB", "TJS", "TMT", "TOP", "TRY", "TTD", "TWD",
    "TZS", "UAH", "USD", "UYU", "UZS", "VED", "VES", "WST", "XCD", "XCG", "YER", "ZAR",
    "ZMW", "ZWG",
)

MINOR_UNITS: dict[str, int] = {}
for _code in _EXPONENT_0:
    MINOR_UNITS[_code] = 0
for _code in _EXPONENT_3:
    MINOR_UNITS[_code] = 3
for _code in _EXPONENT_4:
    MINOR_UNITS[_code] = 4
for _code in _EXPONENT_2:
    MINOR_UNITS[_code] = 2


def normalize_currency(currency: str) -> str:
    """Return the canonical ISO 4217 alphabetic code.

    Args:
        currency: Currency code, possibly with surrounding whitespace or
            lower case.

    Returns:
        Uppercase code present in ``MINOR_UNITS``.

    Raises:
        UnknownCurrencyError: If ``currency`` is not a known ISO code.
    """
    if not isinstance(currency, str):
        raise UnknownCurrencyError(currency)
    code = currency.strip().upper()
    if code not in MINOR_UNITS:
        raise UnknownCurrencyError(currency)
    return code


def minor_unit_places(currency: str) -> int:
    """Return the ISO 4217 minor-unit exponent for ``currency``.

    Args:
        currency: ISO 4217 alphabetic code.

    Returns:
        Number of decimal places (0 for JPY, 2 for USD and TWD, 3 for KWD).

    Raises:
        UnknownCurrencyError: If ``currency`` is not in the table.
    """
    return MINOR_UNITS[normalize_currency(currency)]
