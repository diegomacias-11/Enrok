from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter
def currency(value, decimals=2, symbol="$"):
    """Format number as currency with thousands separators and symbol.

    Usage: {{ value|currency }} or {{ value|currency:0 }} for no decimals.
    """
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    try:
        decs = int(decimals)
    except Exception:
        decs = 2
    fmt = f"{{:,.{decs}f}}"
    return f"{symbol}{fmt.format(d)}"

