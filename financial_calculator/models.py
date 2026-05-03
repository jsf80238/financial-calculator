from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping


@dataclass(frozen=True)
class PathResult:
    """Outcome of one simulated path through month 0 .. horizon_months - 1."""

    is_depleted: bool
    depletion_month: int | None
    """Month index (0-based) when total balance first went to zero or below, if depleted."""

    final_total_balance: float
    """Total balance after the last simulated month (0 if depleted on or before last month)."""


class MarketAssumption(Enum):
    """
    Subtract this amount from each month's return.
    So if the user selects BELOW_AVERAGE, and BELOW_AVERAGE is set to 25%,
    a return of 5% would be changed to 4%, and a return of -5% would be changed to -6%.
    """
    NORMAL = 0.0
    BELOW_AVERAGE = -0.4
    SIGNIFICANTLY_BELOW_AVERAGE = -0.8


class RebalancingApproach(Enum):
    MAINTAIN_RATIOS = 1
    DISTRIBUTE_EQUALLY = 2


@dataclass(frozen=True)
class CashFlow:
    """Income or expense flow (amounts in dollars)."""

    start_month: int
    end_month: int
    amount: float
    annual_inflation_factor: float
    tax_rate: float

    def __post_init__(self) -> None:
        if self.end_month < self.start_month:
            raise ValueError("end_month must be >= start_month")


@dataclass
class Scenario:
    """User scenario: initial allocations and optional cash flows."""

    initial_allocations: Mapping[str, float]
    income_flows: Mapping[str, CashFlow] = field(default_factory=dict)
    expense_flows: Mapping[str, CashFlow] = field(default_factory=dict)
    birthdates: dict = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.initial_allocations:
            raise ValueError("initial_allocations must be non-empty")
        for k, v in self.initial_allocations.items():
            if v < 0:
                raise ValueError(f"Negative allocation for {k!r}")
