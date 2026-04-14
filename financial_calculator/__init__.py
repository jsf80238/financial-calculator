"""Monte Carlo financial calculator (local CLI)."""

from financial_calculator.engine import PathResult, simulate_path
from financial_calculator.models import CashFlow, ReturnMethod, Scenario
from financial_calculator.monte_carlo import MonteCarloSummary, run_monte_carlo
from financial_calculator.returns_data import ReturnsData, load_returns_csv
from financial_calculator.scenario_json import load_scenario_json, scenario_from_json_dict

__all__ = [
    "CashFlow",
    "PathResult",
    "ReturnMethod",
    "ReturnsData",
    "Scenario",
    "MonteCarloSummary",
    "load_returns_csv",
    "load_scenario_json",
    "run_monte_carlo",
    "scenario_from_json_dict",
    "simulate_path",
]
