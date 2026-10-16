"""Canonical monetary arithmetic and quantization utilities for ReHUB.

All financial transactions, totals, line items, taxes, discounts, and general ledger
postings must strictly use Decimal arithmetic with ROUND_HALF_UP to prevent
IEEE-754 floating-point precision divergence.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

MONEY_QUANTUM = Decimal("0.01")


def money(value: Any) -> Decimal:
    """Safely converts and quantizes any input value to standard 2-decimal money (KES).

    Accepts Decimal, str, int, float, or None.
    If float is passed, it is formatted to 4 decimals first to eliminate float
    representation artifacts before quantization.
    """
    if value is None or value == "":
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    if isinstance(value, float):
        value = f"{value:.4f}"
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_money(value: Decimal) -> Decimal:
    """Quantize a Decimal value to standard 2-decimal places using ROUND_HALF_UP."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
