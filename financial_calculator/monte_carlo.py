from __future__ import annotations

import random
from dataclasses import dataclass, field

from financial_calculator.engine import PathResult, simulate_path
from financial_calculator.models import ReturnMethod, Scenario
from financial_calculator.returns_data import ReturnsData


def _percentile_nearest(sorted_vals: list[float], p: float) -> float:
    """p in [0, 100]."""
    if not sorted_vals:
        return float("nan")
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]
    idx = round((p / 100.0) * (len(sorted_vals) - 1))
    return sorted_vals[int(idx)]


@dataclass
class MonteCarloSummary:
    num_paths: int
    horizon_months: int
    num_depleted: int
    num_survived: int
    fraction_depleted: float
    depletion_month_counts: dict[int, int]
    """Histogram: depletion_month -> count (only paths that depleted)."""

    final_balance_mean: float
    final_balance_median: float
    final_balance_p10: float
    final_balance_p90: float
    final_balances_survivors: list[float] = field(repr=False)

    def to_dict(self) -> dict:
        return {
            "num_paths": self.num_paths,
            "horizon_months": self.horizon_months,
            "num_depleted": self.num_depleted,
            "num_survived": self.num_survived,
            "fraction_depleted": self.fraction_depleted,
            "depletion_month_counts": {
                str(k): v for k, v in sorted(self.depletion_month_counts.items())
            },
            "final_balance_mean": self.final_balance_mean,
            "final_balance_median": self.final_balance_median,
            "final_balance_p10": self.final_balance_p10,
            "final_balance_p90": self.final_balance_p90,
        }


def run_monte_carlo(
    scenario: Scenario,
    returns_data: ReturnsData,
    horizon_months: int,
    num_paths: int,
    method: ReturnMethod,
    seed: int | None = None,
) -> MonteCarloSummary:
    if num_paths < 1:
        raise ValueError("num_paths must be at least 1")

    rng = random.Random(seed)
    depleted = 0
    survived = 0
    depletion_months: list[int] = []
    final_survivors: list[float] = []
    counts: dict[int, int] = {}

    for _ in range(num_paths):
        result: PathResult = simulate_path(
            scenario, returns_data, horizon_months, method, rng
        )
        if result.depleted:
            depleted += 1
            if result.depletion_month is not None:
                depletion_months.append(result.depletion_month)
                counts[result.depletion_month] = counts.get(result.depletion_month, 0) + 1
        else:
            survived += 1
            final_survivors.append(result.final_total_balance)

    frac = depleted / num_paths if num_paths else 0.0

    surv_sorted = sorted(final_survivors)
    mean = sum(final_survivors) / len(final_survivors) if final_survivors else float("nan")
    med = _percentile_nearest(surv_sorted, 50.0)
    p10 = _percentile_nearest(surv_sorted, 10.0)
    p90 = _percentile_nearest(surv_sorted, 90.0)

    return MonteCarloSummary(
        num_paths=num_paths,
        horizon_months=horizon_months,
        num_depleted=depleted,
        num_survived=survived,
        fraction_depleted=frac,
        depletion_month_counts=counts,
        final_balance_mean=mean,
        final_balance_median=med,
        final_balance_p10=p10,
        final_balance_p90=p90,
        final_balances_survivors=final_survivors,
    )
