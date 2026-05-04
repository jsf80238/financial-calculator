from dataclasses import dataclass
# Imports above are standard Python
# Imports below are 3rd-party
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
from financial_calculator.models import CashFlow, Scenario, PathResult, MarketAssumption, RebalancingApproach
from base import Logger, RETURNS_PATH

logger = Logger().get_logger()
# 1. Load the Master History once
master_history_df = pd.read_csv(RETURNS_PATH / "master_history.csv", index_col="Date")


def _monthly_inflation_rate(annual_factor: float) -> float:
    return (1.0 + annual_factor) ** (1.0 / 12.0) - 1.0


def _flow_nominal_for_month(flow: CashFlow, month_index: int) -> float:
    if month_index < flow.start_month or month_index > flow.end_month:
        return 0.0
    r_m = _monthly_inflation_rate(flow.annual_inflation_factor)
    return flow.amount * ((1.0 + r_m) ** month_index)


def _sum_income(scenario: Scenario, month_index: int) -> float:
    result = 0.0
    for flow_name in scenario.income_flows:
        flow_income = _flow_nominal_for_month(scenario.income_flows[flow_name], month_index)
        flow_income *= 1 - scenario.income_flows[flow_name].tax_rate
        result += flow_income
    return result


def _sum_expense(scenario: Scenario, month_index: int) -> float:
    return sum(_flow_nominal_for_month(f, month_index) for f in scenario.expense_flows.values())


def _add_income_or_subtract_expense(
        description: str,
        balance_dict: dict,
        amount_to_distribute: float,
        rebalancing_approach: RebalancingApproach
) -> None:
    if rebalancing_approach == RebalancingApproach.DISTRIBUTE_EQUALLY:
        logger.debug(f"Applying {description} ${amount_to_distribute:,.2f} equally to accounts ...")
        for index_name, current_value in balance_dict.items():
            amount = amount_to_distribute / len(balance_dict)
            balance_dict[index_name] += amount
            logger.debug(f"${amount:,.2f} to {index_name} ...")
    else:
        total_balances = sum(balance_dict.values())
        balance_ratio_dict = {k: v / total_balances for k, v in balance_dict.items()}
        logger.debug(f"Applying {description} ${amount_to_distribute:,.2f} in these ratios: {balance_ratio_dict} ...")
        for index_name, current_value in balance_dict.items():
            amount = amount_to_distribute * balance_ratio_dict[index_name]
            balance_dict[index_name] += amount
            logger.debug(f"${amount:,.2f} to {index_name} ...")


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

    balance_dict: dict[str, float] = {
        k: float(v) for k, v in scenario.initial_allocations.items()
    }

    # Pick a random sequence of row indices
    random_indices = np.random.choice(len(master_history_df), size=horizon_months, replace=True)
    # Grab the entire block of returns for all assets in the journey
    # Columns will be sorted alphabetically
    journey_returns = master_history_df.iloc[random_indices]
    random_path_dict = journey_returns.to_dict(orient='list')

    for month_index in range(1, horizon_months+1):
        logger.info(f"Month {month_index}.")
        logger.info(f"Current balances: {", ".join(f'{k}=${int(v):,d}' for k, v in balance_dict.items())}")
        logger.info(f"Total balance: ${int(sum(balance_dict.values())):,d}")
        # Add from income streams and subtract from expense streams
        income_to_distribute = _sum_income(scenario, month_index)
        _add_income_or_subtract_expense("monthly income", balance_dict, income_to_distribute, rebalancing_approach)
        expense_to_distribute = _sum_expense(scenario, month_index)
        _add_income_or_subtract_expense("monthly expense", balance_dict, -expense_to_distribute, rebalancing_approach)
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
            _add_income_or_subtract_expense("unapplied investment loss", balance_dict, total_negative, rebalancing_approach)

        # Add/subtract based on investment return
        for index_name in index_name_list:
            monthly_return = random_path_dict[index_name][month_index]
            if market_assumption.value != 0:
                monthly_return += (market_assumption.value * monthly_return)
                logger.info(f"Reducing return by {market_assumption.value * 100:,.2f}% for {index_name}...")
            # Calculate the dollar change for THIS month
            current_balance = balance_dict[index_name]
            delta = current_balance * monthly_return
            # Update the balance for the NEXT month
            balance_dict[index_name] = current_balance + delta
            delta_percent = monthly_return * 100
            logger.debug(f"Applying investment return of {delta_percent:,.2f}% (${delta:,.2f}) to {index_name} ...")

        if sum(balance_dict.values()) <= 0:
            return PathResult(
                is_depleted=True,
                depletion_month=month_index,
                final_total_balance=0.0,
            )

    return PathResult(
        is_depleted=False,
        depletion_month=None,
        final_total_balance=float(sum(balance_dict.values())),
    )


if __name__ == "__main__":
    from financial_calculator.scenario import load_scenario
    from pathlib import Path
    # logger.setLevel("WARN")
    logger.setLevel("DEBUG")
    Logger().set_file("/tmp/financial.log")
    path_result = simulate_path(
        scenario=load_scenario(Path(__file__).parent.parent / "example_scenario.yaml"),
        horizon_months=40*12,
        market_assumption=MarketAssumption.NORMAL,
        rebalancing_approach=RebalancingApproach.MAINTAIN_RATIOS,
    )
    logger.warning(path_result)