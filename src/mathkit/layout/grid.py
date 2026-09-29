"""Canonical quantization grid shared by all engines."""

from decimal import ROUND_HALF_EVEN, Decimal

#: The layout bounding box is ``[0, GRID]²``, i.e. a 1/10⁴ grid on the unit square.
GRID = 10_000


def quantize(value: Decimal) -> int:
    """Round a grid coordinate half-to-even."""
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
