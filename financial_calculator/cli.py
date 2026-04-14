from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from financial_calculator.models import ReturnMethod
from financial_calculator.monte_carlo import run_monte_carlo
from financial_calculator.returns_data import load_returns_csv
from financial_calculator.scenario_json import load_scenario_json


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Monte Carlo financial calculator (local)",
    )
    p.add_argument(
        "scenario",
        type=Path,
        help="Path to scenario JSON file",
    )
    p.add_argument(
        "--returns",
        type=Path,
        default=Path("historical_data/monthly_returns.csv"),
        help="Path to monthly_returns.csv",
    )
    p.add_argument(
        "--horizon-months",
        type=int,
        required=True,
        help="Simulation length in months (>= 1)",
    )
    p.add_argument(
        "--paths",
        type=int,
        required=True,
        help="Number of Monte Carlo paths",
    )
    p.add_argument(
        "--method",
        choices=[m.value for m in ReturnMethod],
        default=ReturnMethod.normal.value,
        help="Return sampling method",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed (optional, for reproducibility)",
    )
    p.add_argument(
        "--json-out",
        action="store_true",
        help="Print summary as JSON only",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scenario = load_scenario_json(args.scenario)
    returns_path = args.returns
    if not returns_path.is_file():
        print(f"Returns file not found: {returns_path}", file=sys.stderr)
        return 1

    returns_data = load_returns_csv(returns_path)
    method = ReturnMethod(args.method)

    summary = run_monte_carlo(
        scenario,
        returns_data,
        horizon_months=args.horizon_months,
        num_paths=args.paths,
        method=method,
        seed=args.seed,
    )

    if args.json_out:
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print(f"Paths: {summary.num_paths}, horizon: {summary.horizon_months} months")
        print(f"Depleted: {summary.num_depleted} ({summary.fraction_depleted:.2%})")
        print(f"Survived: {summary.num_survived}")
        if summary.depletion_month_counts:
            print("Depletion month (histogram):", summary.depletion_month_counts)
        if summary.num_survived > 0:
            print("Final balance (survivors):")
            print(f"  mean:   {summary.final_balance_mean:,.2f}")
            print(f"  median: {summary.final_balance_median:,.2f}")
            print(f"  p10:    {summary.final_balance_p10:,.2f}")
            print(f"  p90:    {summary.final_balance_p90:,.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
