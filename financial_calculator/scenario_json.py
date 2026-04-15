from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_calculator.models import CashFlow, Scenario


def _flow_from_dict(d: Any) -> CashFlow:
    if not isinstance(d, dict):
        raise TypeError("flow must be an object")
    return CashFlow(
        start_month=int(d["start_month"]),
        end_month=int(d["end_month"]),
        amount=float(d["amount"]),
        annual_inflation_factor=float(d["annual_inflation_factor"]),
    )


def scenario_from_json_dict(data: dict[str, Any]) -> Scenario:
    if "initial_allocations" not in data:
        raise ValueError("JSON must contain initial_allocations")
    alloc = data["initial_allocations"]
    if not isinstance(alloc, dict):
        raise TypeError("initial_allocations must be an object")
    initial = {str(k): float(v) for k, v in alloc.items()}

    income_raw = data.get("income_flows", [])
    expense_raw = data.get("expense_flows", [])
    if not isinstance(income_raw, list):
        raise TypeError("income_flows must be an array")
    if not isinstance(expense_raw, list):
        raise TypeError("expense_flows must be an array")

    income_flows = [_flow_from_dict(x) for x in income_raw]
    expense_flows = [_flow_from_dict(x) for x in expense_raw]

    prior_raw = data.get("mean_shrinkage_prior")
    shrink_prior: dict[str, float] | None = None
    if prior_raw is not None:
        if not isinstance(prior_raw, dict):
            raise TypeError("mean_shrinkage_prior must be an object")
        shrink_prior = {str(k): float(v) for k, v in prior_raw.items()}

    return Scenario(
        initial_allocations=initial,
        income_flows=income_flows,
        expense_flows=expense_flows,
        mean_shrinkage_prior=shrink_prior,
    )


def load_scenario_json(path: Path | str) -> Scenario:
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("scenario JSON must be an object")
    return scenario_from_json_dict(data)
