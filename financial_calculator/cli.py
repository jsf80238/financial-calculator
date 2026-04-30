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
from financial_calculator.models import MarketAssumption, RebalancingApproach
from financial_calculator.monte_carlo import run_monte_carlo
from financial_calculator.scenario import load_scenario
from financial_calculator.engine import simulate_path

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
market_assumption_choices = MarketAssumption.__members__.keys()
market_assumption_default = MarketAssumption.NORMAL
p.add_argument(
    "--market-assumption",
    choices=market_assumption_choices,
    default=market_assumption_default,
    help=f"One of {'/'.join(market_assumption_choices)}, default is '{market_assumption_default}'",
)
rebalancing_approach = RebalancingApproach.__members__.keys()
rebalancing_approach_default = RebalancingApproach.DISTRIBUTE_EQUALLY
p.add_argument(
    "--rebalancing-approach",
    choices=rebalancing_approach,
    default=rebalancing_approach_default,
    help=f"One of {'/'.join(rebalancing_approach)}, default is '{rebalancing_approach_default}'",
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
iterations = args.iterations
horizon_months = args.horizon_months

path_num = 1
depleted, survived = 0, 0
final_survivor_list = list()
for _ in enumerate(range(iterations), 1):
    if path_num % 10 == 0:
        logger.info(f"Monte Carlo path {path_num}/{iterations}")
    path_num += 1
    result: PathResult = simulate_path(
        scenario=scenario,
        horizon_months=horizon_months,
        market_assumption=market_assumption,
        rebalancing_approach=rebalancing_approach,
    )
    if result.is_depleted:
        depleted += 1
        if result.depletion_month is not None:
            depletion_months.append(result.depletion_month)
            counts[result.depletion_month] = counts.get(result.depletion_month, 0) + 1
    else:
        survived += 1
        final_survivor_list.append(result.final_total_balance)

frac = depleted / iterations if iterations else 0.0

surv_sorted = sorted(final_survivor_list)
mean = sum(final_survivor_list) / len(final_survivor_list) if final_survivor_list else float("nan")
med = _percentile_nearest(surv_sorted, 50.0)
p10 = _percentile_nearest(surv_sorted, 10.0)
p90 = _percentile_nearest(surv_sorted, 90.0)

if args.json_out:
    print(json.dumps(summary.to_dict(), indent=2))
else:
    print(f"Paths: {summary.iterations}, horizon: {summary.horizon_months} months")
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
