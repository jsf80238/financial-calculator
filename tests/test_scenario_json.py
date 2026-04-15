import json

from financial_calculator.scenario_json import scenario_from_json_dict


def test_scenario_from_json_dict():
    data = {
        "initial_allocations": {"a": 1.0, "b": 2.0},
        "income_flows": [
            {
                "start_month": 0,
                "end_month": 5,
                "amount": 100.0,
                "annual_inflation_factor": 0.02,
            }
        ],
        "expense_flows": [],
    }
    s = scenario_from_json_dict(data)
    assert s.initial_allocations["a"] == 1.0
    assert len(s.income_flows) == 1
    assert s.income_flows[0].end_month == 5


def test_mean_shrinkage_prior_from_json():
    data = {
        "initial_allocations": {"x": 10.0},
        "mean_shrinkage_prior": {"x": 0.001},
    }
    s = scenario_from_json_dict(data)
    assert s.mean_shrinkage_prior is not None
    assert s.mean_shrinkage_prior["x"] == 0.001


def test_round_trip_json(tmp_path):
    p = tmp_path / "s.json"
    obj = {
        "initial_allocations": {"x": 10.0},
        "income_flows": [],
        "expense_flows": [],
    }
    p.write_text(json.dumps(obj), encoding="utf-8")
    from financial_calculator.scenario_json import load_scenario_json

    s = load_scenario_json(p)
    assert list(s.initial_allocations.keys()) == ["x"]
