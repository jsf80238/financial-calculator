"""Monte Carlo financial calculator (local CLI)."""

from financial_calculator.engine import PathResult, simulate_path
from financial_calculator.models import (
    CashFlow,
    MarketAssumption,
    Scenario,
    shrinkage_lambda_for_market_assumption,
)
from financial_calculator.monte_carlo import MonteCarloSummary, run_monte_carlo
from financial_calculator.returns_data import ParametricReturnModel, ReturnsData, load_returns_csv
from financial_calculator.scenario_json import load_scenario_json, scenario_from_json_dict

__all__ = [
    "CashFlow",
    "MarketAssumption",
    "ParametricReturnModel",
    "PathResult",
    "ReturnsData",
    "Scenario",
    "MonteCarloSummary",
    "load_returns_csv",
    "load_scenario_json",
    "run_monte_carlo",
    "scenario_from_json_dict",
    "shrinkage_lambda_for_market_assumption",
    "simulate_path",
]
