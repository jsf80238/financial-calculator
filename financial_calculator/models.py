from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping


class MarketAssumption(str, Enum):
    """
    How much to blend fitted sample means with ``mean_shrinkage_prior``:

    Per index: ``μ = λ × fitted_mean + (1−λ) × prior`` (covariance from history).
    """

    normal = "normal"
    """λ = 1 — use sample means only; prior is ignored."""

    below_average = "below_average"
    """λ = 0.85 — 15% weight on prior, 85% on sample mean."""

    significantly_below_average = "significantly_below_average"
    """λ = 0.70 — 30% weight on prior, 70% on sample mean."""


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
    income_flows: Mapping[str, CashFlow] = field(default_factory=dict)
    expense_flows: Mapping[str, CashFlow] = field(default_factory=dict)
    #: Monthly return anchor per index (decimal) when ``--market-assumption`` is
    #: ``below_average`` or ``significantly_below_average``. Omitted indices default to ``0``.
    mean_shrinkage_prior: Mapping[str, float] | None = None
    birthdates: dict = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.initial_allocations:
            raise ValueError("initial_allocations must be non-empty")
        for k, v in self.initial_allocations.items():
            if v < 0:
                raise ValueError(f"Negative allocation for {k!r}")
