import random

from financial_calculator.engine import simulate_path, _flow_nominal_for_month
from financial_calculator.models import CashFlow, ReturnMethod, Scenario
from financial_calculator.returns_data import load_returns_csv


def test_flow_inflation_compounding():
    f = CashFlow(
        start_month=2,
        end_month=4,
        amount=1000.0,
        annual_inflation_factor=0.0,
    )
    assert _flow_nominal_for_month(f, 1) == 0.0
    assert _flow_nominal_for_month(f, 2) == 1000.0
    r_m = (1.0 + 0.0) ** (1.0 / 12.0) - 1.0  # 0
    assert _flow_nominal_for_month(f, 3) == 1000.0 * ((1.0 + r_m) ** 1)
    assert _flow_nominal_for_month(f, 4) == 1000.0 * ((1.0 + r_m) ** 2)


def test_one_month_ledger_zero_returns(zero_returns_path):
    """Returns 0; income 100 and expense 100 net to original split."""
    data = load_returns_csv(zero_returns_path)
    scenario = Scenario(
        initial_allocations={"a": 600.0, "b": 400.0},
        income_flows=[
            CashFlow(0, 0, 100.0, 0.0),
        ],
        expense_flows=[
            CashFlow(0, 0, 100.0, 0.0),
        ],
    )
    rng = random.Random(42)
    result = simulate_path(scenario, data, horizon_months=1, method=ReturnMethod.normal, rng=rng)
    assert not result.depleted
    assert result.depletion_month is None
    assert abs(result.final_total_balance - 1000.0) < 1e-9


def test_depletion_high_expense(zero_returns_path):
    data = load_returns_csv(zero_returns_path)
    scenario = Scenario(
        initial_allocations={"a": 100.0, "b": 100.0},
        expense_flows=[
            CashFlow(0, 0, 500.0, 0.0),
        ],
    )
    rng = random.Random(0)
    result = simulate_path(scenario, data, horizon_months=1, method=ReturnMethod.normal, rng=rng)
    assert result.depleted
    assert result.depletion_month == 0
