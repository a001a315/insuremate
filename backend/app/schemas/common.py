from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


def mask_policy_number(n: str) -> str:
    return n if len(n) <= 4 else "•" * (len(n) - 4) + n[-4:]
