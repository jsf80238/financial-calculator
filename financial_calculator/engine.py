from dataclasses import dataclass
# Imports above are standard Python
# Imports below are 3rd-party
import numpy as np
import pyarrow.parquet as pq
from financial_calculator.models import CashFlow, Scenario, PathResult, MarketAssumption, RebalancingApproach
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
    rebalancing_approach: RebalancingApproach,
) -> PathResult:
    """
    One Monte Carlo path. Monthly order: returns → income (split) → expense (split).
    """
    index_name_list = list(scenario.initial_allocations.keys())
    random_path_dict = dict()
    for index_name in index_name_list:
        random_path_dict[index_name] = get_random_path(index_name)

    balance_dict: dict[str, float] = {
        k: float(v) for k, v in scenario.initial_allocations.items()
    }
    initial_balance_dict = balance_dict.copy()

    for month_index in range(1, horizon_months+1):
        logger.info(f"Month {month_index}.")
        logger.info(f"Current balances: {", ".join(f'{k}=${int(v):,d}' for k, v in balance_dict.items())}")
        logger.info(f"Total balance: ${int(sum(balance_dict.values())):,d}")
        # Add from income streams and subtract from expense streams
        income_to_distribute = _sum_income(scenario, month_index)
        expense_to_distribute = _sum_expense(scenario, month_index)
        if rebalancing_approach == RebalancingApproach.DISTRIBUTE_EQUALLY:
            logger.info(f"Adding income of ${income_to_distribute:.2f} equally to accounts ...")
            for index_name, current_value in balance_dict.items():
                balance_dict[index_name] += income_to_distribute / len(balance_dict)
            logger.info(f"Subtracting expense of ${expense_to_distribute:.2f} equally from accounts ...")
            for index_name, current_value in balance_dict.items():
                balance_dict[index_name] -= expense_to_distribute / len(balance_dict)
        else:
            total_balances = sum(balance_dict.values())
            balance_ratio_dict = {k: v / total_balances for k, v in balance_dict.items()}
            logger.info(f"Adding income of ${income_to_distribute:.2f} in these ratios: {balance_ratio_dict} ...")
            for index_name, current_value in balance_dict.items():
                balance_dict[index_name] += income_to_distribute * balance_ratio_dict[index_name]
            logger.info(f"Subtracting expense of ${expense_to_distribute:.2f} in these ratios: {balance_ratio_dict} ...")
            for index_name, current_value in balance_dict.items():
                balance_dict[index_name] -= expense_to_distribute * balance_ratio_dict[index_name]
        # Drop indexes with balances <= 0
        # Distribute that negative value according to rebalancing_approach
        total_negative = 0
        for index_name in frozenset(balance_dict.keys()):
            if balance_dict[index_name] <= 0:
                total_negative += balance_dict[index_name]
                del balance_dict[index_name]
                index_name_list.remove(index_name)
                logger.info(f"Dropping index {index_name} because its balance fell to $0.")
        if total_negative < 0:
            if rebalancing_approach == RebalancingApproach.DISTRIBUTE_EQUALLY:
                logger.info(f"Subtracting negative balance of ${total_negative:.2f} equally from accounts ...")
                for index_name, current_value in balance_dict.items():
                    balance_dict[index_name] -= total_negative / len(balance_dict)
            else:
                total_balances = sum(balance_dict.values())
                balance_ratio_dict = {k: v / total_balances for k, v in balance_dict.items()}
                logger.info(f"Subtracting negative balance of ${total_negative:.2f} in these ratios: {balance_ratio_dict} ...")
                for index_name, current_value in balance_dict.items():
                    balance_dict[index_name] -= total_negative * balance_ratio_dict[index_name]
        # Add/subtract based on investment return
        for index_name in index_name_list:
            investment_return = random_path_dict[index_name][month_index] / 100  # Values are based on a $100 initial investment
            new_balance = initial_balance_dict[index_name] * investment_return
            delta = int(new_balance - balance_dict[index_name])
            delta_percent = 100 * delta / balance_dict[index_name]
            logger.info(f"Applying investment return of {delta_percent:.2f}% (${delta:,d}) to {index_name} ...")
            balance_dict[index_name] += new_balance

        if sum(balance_dict.values()) <= 0:
            return PathResult(
                is_depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

    return PathResult(
        is_depleted=False,
        depletion_month=None,
        final_total_balance=sum(balance_dict.values()),
    )


if __name__ == "__main__":
    from financial_calculator.scenario import load_scenario
    from pathlib import Path
    simulate_path(
        scenario=load_scenario(Path(__file__).parent.parent / "example_scenario.yaml"),
        horizon_months=50*12,
        market_assumption=MarketAssumption.BELOW_AVERAGE,
        rebalancing_approach=RebalancingApproach.DISTRIBUTE_EQUALLY,
    )