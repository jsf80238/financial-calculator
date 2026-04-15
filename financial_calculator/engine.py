from __future__ import annotations

from dataclasses import dataclass

from numpy.random import Generator

from financial_calculator.models import CashFlow, MarketAssumption, Scenario, shrinkage_lambda_for_market_assumption
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
    return sum(_flow_nominal_for_month(f, month_index) for f in scenario.income_flows.values())


def _sum_expense(scenario: Scenario, month_index: int) -> float:
    return sum(_flow_nominal_for_month(f, month_index) for f in scenario.expense_flows.values())


def simulate_path(
    scenario: Scenario,
    returns_data: ReturnsData,
    horizon_months: int,
    market_assumption: MarketAssumption,
    rng: Generator,
) -> PathResult:
    """
    One Monte Carlo path. Monthly order: returns → income (split) → expense (split).

    Investment returns are multivariate Normal with mean from **shrinkage**
    (``--market-assumption`` sets λ toward ``mean_shrinkage_prior``); covariance from history.
    """
    if horizon_months < 1:
        raise ValueError("horizon_months must be at least 1")

    indices = tuple(sorted(scenario.initial_allocations.keys()))
    returns_data.require_indices(set(indices))
    # prior = (
    #     dict(scenario.mean_shrinkage_prior)
    #     if scenario.mean_shrinkage_prior is not None
    #     else None
    # )
    lam = shrinkage_lambda_for_market_assumption(market_assumption)
    model = returns_data.parametric_model(
        indices,
        shrinkage_lambda=lam,
        shrinkage_prior=None,
    )

    total_init = sum(scenario.initial_allocations.values())
    if total_init <= 0:
        raise ValueError("initial allocations must sum to a positive total")

    balances: dict[str, float] = {
        k: float(v) for k, v in scenario.initial_allocations.items()
    }

    for month_index in range(horizon_months):
        month_returns = model.sample_month_returns(rng)

        for name in indices:
            r = month_returns[name]
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
