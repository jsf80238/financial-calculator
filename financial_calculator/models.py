from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class ReturnMethod(str, Enum):
    normal = "normal"
    below_average = "below_average"
    significantly_below_average = "significantly_below_average"


@dataclass(frozen=True)
class CashFlow:
    """Income or expense flow (amounts in dollars)."""

    start_month: int
    end_month: int
    amount: float
    annual_inflation_factor: float

    def __post_init__(self) -> None:
        if self.end_month < self.start_month:
            raise ValueError("end_month must be >= start_month")


@dataclass
class Scenario:
    """User scenario: initial allocations and optional cash flows."""

    initial_allocations: Mapping[str, float]
    income_flows: list[CashFlow] = field(default_factory=list)
    expense_flows: list[CashFlow] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.initial_allocations:
            raise ValueError("initial_allocations must be non-empty")
        for k, v in self.initial_allocations.items():
            if v < 0:
                raise ValueError(f"Negative allocation for {k!r}")
