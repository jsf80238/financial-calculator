import json
from pathlib import Path
from typing import Any

import yaml

from financial_calculator.models import CashFlow, Scenario


def _flow_from_dict(d: Any) -> CashFlow:
    if not isinstance(d, dict):
        raise TypeError("flow must be a mapping")
    return CashFlow(
        start_month=int(d["start_month"]),
        end_month=int(d["end_month"]),
        amount=float(d["amount"]),
        annual_inflation_factor=float(d["annual_inflation_factor"]),
    )


def _flows_from_mapping(raw: Any, field_name: str) -> dict[str, CashFlow]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TypeError(f"{field_name} must be a mapping of name -> flow object")
    return {str(k): _flow_from_dict(v) for k, v in raw.items()}


def scenario_from_dict(data: dict[str, Any]) -> Scenario:
    if "initial_allocations" not in data:
        raise ValueError("scenario must contain initial_allocations")
    alloc = data["initial_allocations"]
    if not isinstance(alloc, dict):
        raise TypeError("initial_allocations must be a mapping")
    initial_amount = sum(alloc.values())
    if initial_amount <= 0:
        raise ValueError("initial allocations must sum to positive amount")
    initial_allocations_dict = {str(k): float(v) for k, v in alloc.items()}
    birthdates = data.get("birthdates")

    income_flows = _flows_from_mapping(data.get("income_flows"), "income_flows")
    expense_flows = _flows_from_mapping(data.get("expense_flows"), "expense_flows")

    return Scenario(
        initial_allocations=initial_allocations_dict,
        income_flows=income_flows,
        expense_flows=expense_flows,
        birthdates=birthdates,
    )


def load_scenario(path: Path | str) -> Scenario:
    """Load a scenario from ``.yaml`` / ``.yml`` or ``.json``."""
    p = Path(path)
    suffix = p.suffix.lower()
    text = p.read_text(encoding="utf-8")

    if suffix in (".yaml", ".yml"):
        loaded = yaml.safe_load(text)
    elif suffix == ".json":
        loaded = json.loads(text)
    else:
        raise ValueError(
            f"Unsupported scenario file type {suffix!r}; use .yaml, .yml, or .json"
        )

    if not isinstance(loaded, dict):
        raise ValueError("scenario file must contain a mapping at the top level")
    return scenario_from_dict(loaded)


if __name__ == "__main__":
    scenario_file_path = Path(__file__).parent.parent / "example_scenario.yaml"
    import pprint
    pprint.pprint(load_scenario(scenario_file_path))