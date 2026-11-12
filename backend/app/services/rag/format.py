from datetime import date
from decimal import Decimal


def inr(n) -> str:
    n = int(round(Decimal(n or 0)))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{'-' if n < 0 else ''}₹{s}"


def fmt_date(d: date | None) -> str:
    return d.strftime("%d %b %Y") if d else "not recorded"
