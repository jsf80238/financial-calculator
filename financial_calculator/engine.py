from dataclasses import dataclass
# Imports above are standard Python
# Imports below are 3rd-party
import numpy as np
import pyarrow.parquet as pq
from financial_calculator.models import CashFlow, MarketAssumption, Scenario, PathResult
from base import Logger, RETURNS_PATH

logger = Logger().get_logger()


def get_random_path(index_name: str):
    # 1. Open the Parquet file (metadata only)
    filepath = RETURNS_PATH / f"{index_name}.parquet"
    pfile = pq.ParquetFile(filepath)

    # 2. Pick a random row group
    # Since we saved in chunks of 100k, there are 10 groups in 1M sims
    num_groups = pfile.num_row_groups
    random_group_idx = np.random.randint(0, num_groups)

    logger.debug(f"Reading from row group {random_group_idx} of {num_groups}...")

    # 3. Load only that specific row group into a DataFrame
    table = pfile.read_row_group(random_group_idx)
    df_chunk = table.to_pandas()

    # 4. Pick one random row (simulation) from this chunk
    random_sim = df_chunk.sample(n=1)

    # Convert to a Series for easier plotting (transpose so index is Month)
    path_series = random_sim.iloc[0]
    path_series.index = [int(m[1:]) for m in path_series.index]  # Convert 'M001' to 1

    return path_series


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
    horizon_months: int,
    market_assumption: MarketAssumption,
) -> PathResult:
    """
    One Monte Carlo path. Monthly order: returns → income (split) → expense (split).
    """
    indices = tuple(sorted(scenario.initial_allocations.keys()))
    random_path_dict = dict()
    for index_name in indices:
        random_path_dict[index_name] = get_random_path(index_name)

    # total_init = sum(scenario.initial_allocations.values())

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
                is_depleted=True,
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
                is_depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

        if expense >= total_after_income:
            return PathResult(
                is_depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

        if expense > 0.0:
            for name in indices:
                balances[name] -= expense * balances[name] / total_after_income

        total_end = sum(balances.values())
        if total_end <= 0:
            return PathResult(
                is_depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

    return PathResult(
        is_depleted=False,
        depletion_month=None,
        final_total_balance=sum(balances.values()),
    )
