from __future__ import annotations

import random
from dataclasses import dataclass

from financial_calculator.models import CashFlow, ReturnMethod, Scenario
from financial_calculator.returns_data import ReturnsData


@dataclass(frozen=True)
class PathResult:
    """Outcome of one simulated path through month 0 .. horizon_months - 1."""

    depleted: bool
    depletion_month: int | None
    """Month index (0-based) when total balance first went to zero or below, if depleted."""

    final_total_balance: float
    """Total balance after the last simulated month (0 if depleted on or before last month)."""


def _monthly_inflation_rate(annual_factor: float) -> float:
    return (1.0 + annual_factor) ** (1.0 / 12.0) - 1.0


def _flow_nominal_for_month(flow: CashFlow, month_index: int) -> float:
    if month_index < flow.start_month or month_index > flow.end_month:
        return 0.0
    r_m = _monthly_inflation_rate(flow.annual_inflation_factor)
    elapsed = month_index - flow.start_month
    return flow.amount * ((1.0 + r_m) ** elapsed)


def _sum_income(scenario: Scenario, month_index: int) -> float:
    return sum(_flow_nominal_for_month(f, month_index) for f in scenario.income_flows)


def _sum_expense(scenario: Scenario, month_index: int) -> float:
    return sum(_flow_nominal_for_month(f, month_index) for f in scenario.expense_flows)


def _draw_return(
    rng: random.Random,
    returns_data: ReturnsData,
    method: ReturnMethod,
    index_name: str,
) -> float:
    pool = returns_data.by_name[index_name].pool(method)
    return rng.choice(pool)


def simulate_path(
    scenario: Scenario,
    returns_data: ReturnsData,
    horizon_months: int,
    method: ReturnMethod,
    rng: random.Random,
) -> PathResult:
    """
    One Monte Carlo path. Monthly order: returns → income (split) → expense (split).

    Raises ValueError if portfolio total is zero when income or expense needs splitting.
    """
    if horizon_months < 1:
        raise ValueError("horizon_months must be at least 1")

    indices = list(scenario.initial_allocations.keys())
    returns_data.require_indices(set(indices))

    total_init = sum(scenario.initial_allocations.values())
    if total_init <= 0:
        raise ValueError("initial allocations must sum to a positive total")

    balances: dict[str, float] = {k: float(v) for k, v in scenario.initial_allocations.items()}

    for month_index in range(horizon_months):
        # 1) Investment returns (independent draw per index)
        for name in indices:
            r = _draw_return(rng, returns_data, method, name)
            balances[name] *= 1.0 + r

        total_after_returns = sum(balances.values())
        if total_after_returns <= 0:
            return PathResult(
                depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

        income = _sum_income(scenario, month_index)
        expense = _sum_expense(scenario, month_index)

        # 2) Income proportional to balances after returns
        if income != 0.0:
            for name in indices:
                balances[name] += income * balances[name] / total_after_returns

        total_after_income = sum(balances.values())
        if total_after_income <= 0:
            return PathResult(
                depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

        # 3) Expense proportional to balances after income
        if expense >= total_after_income:
            return PathResult(
                depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

        if expense > 0.0:
            for name in indices:
                balances[name] -= expense * balances[name] / total_after_income

        total_end = sum(balances.values())
        if total_end <= 0:
            return PathResult(
                depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

    return PathResult(
        depleted=False,
        depletion_month=None,
        final_total_balance=sum(balances.values()),
    )
