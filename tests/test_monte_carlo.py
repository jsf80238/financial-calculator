import pytest

from financial_calculator.models import MarketAssumption, Scenario
from financial_calculator.monte_carlo import run_monte_carlo
from financial_calculator.returns_data import load_returns_csv


def test_run_monte_carlo_zero_returns(zero_returns_path):
    data = load_returns_csv(zero_returns_path)
    scenario = Scenario(initial_allocations={"a": 100.0, "b": 100.0})
    summary = run_monte_carlo(
        scenario,
        data,
        horizon_months=5,
        num_paths=10,
        market_assumption=MarketAssumption.normal,
        seed=0,
    )
    assert summary.num_paths == 10
    assert summary.num_depleted == 0
    assert len(summary.final_balances_survivors) == 10
    assert all(abs(b - 200.0) < 1e-4 for b in summary.final_balances_survivors)


def test_num_paths_validation(zero_returns_path):
    data = load_returns_csv(zero_returns_path)
    scenario = Scenario(initial_allocations={"a": 1.0, "b": 1.0})
    with pytest.raises(ValueError, match="num_paths"):
        run_monte_carlo(
            scenario,
            data,
            horizon_months=1,
            num_paths=0,
            market_assumption=MarketAssumption.normal,
            seed=0,
        )
