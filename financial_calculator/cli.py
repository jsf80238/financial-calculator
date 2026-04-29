from __future__ import annotations

import argparse
import collections
from datetime import datetime
import json
import statistics
import sys
from pathlib import Path
# Imports above are standard Python
# Imports below are 3rd-party
from base import Logger, RETURNS_PATH
from financial_calculator.models import MarketAssumption
from financial_calculator.monte_carlo import run_monte_carlo
from financial_calculator.returns_data import load_returns_csv
from financial_calculator.scenario_io import load_scenario

logger = Logger().get_logger()

p = argparse.ArgumentParser(
    description="Monte Carlo financial calculator (local)",
)
p.add_argument(
    "--scenario",
    type=Path,
    help="Path to scenario file (.yaml / .yml / .json)",
    default=Path(__file__).parent.parent / "example_scenario.yaml",
)
p.add_argument(
    "--horizon-months",
    metavar="NUMBER",
    type=int,
    # required=True,
    help="Simulation length in months (>= 1)",
    default=420,
)
p.add_argument(
    "--iterations",
    metavar="NUMBER",
    type=int,
    # required=True,
    help="Number of Monte Carlo simulations to run",
    default=200,
)
market_assumption_choices = [m.value for m in MarketAssumption]
p.add_argument(
    "--market-assumption",
    choices=market_assumption_choices,
    default=MarketAssumption.normal.value,
    help=f"One of {'/'.join(market_assumption_choices)}, default: {MarketAssumption.normal.value}",
)
# p.add_argument(
#     "--seed",
#     type=int,
#     default=None,
#     help="RNG seed (optional, for reproducibility)",
# )
p.add_argument(
    "--json-out",
    action="store_true",
    help="Print summary as JSON only",
)

args = p.parse_args()
scenario = load_scenario(args.scenario)
market_assumption = MarketAssumption(args.market_assumption)

summary = run_monte_carlo(
    scenario,
    None,
    horizon_months=args.horizon_months,
    num_paths=args.iterations,
    market_assumption=market_assumption,
    seed=args.seed,
)

if args.json_out:
    print(json.dumps(summary.to_dict(), indent=2))
else:
    print(f"Paths: {summary.num_paths}, horizon: {summary.horizon_months} months")
    print(f"Depleted: {summary.num_depleted} ({summary.fraction_depleted:.2%})")
    print(f"Survived: {summary.num_survived} ({1-summary.fraction_depleted:.2%})")
    depletion_month_counter = collections.Counter(summary.depletion_month_counts)
    if summary.depletion_month_counts:
        depletion_month_counter[summary.horizon_months] += summary.num_survived
        print("Depletion month (histogram):", summary.depletion_month_counts)
    # if summary.num_survived > 0:
    #     print("Final balance (survivors):")
    #     print(f"  mean:   {summary.final_balance_mean:,.2f}")
    #     print(f"  median: {summary.final_balance_median:,.2f}")
    #     print(f"  p10:    {summary.final_balance_p10:,.2f}")
    #     print(f"  p90:    {summary.final_balance_p90:,.2f}")
    median_depletion_month = statistics.median(depletion_month_counter.elements())
    median_depletion_as_year_month = datetime.today()
    print("Median depletion month:", )
