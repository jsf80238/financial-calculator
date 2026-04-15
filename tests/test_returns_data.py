import numpy as np

from financial_calculator.models import MarketAssumption, shrinkage_lambda_for_market_assumption
from financial_calculator.returns_data import load_returns_csv


def test_parametric_model_mu_hat(tiny_returns_path):
    data = load_returns_csv(tiny_returns_path)
    model = data.parametric_model(("a", "b"))
    assert model.indices == ("a", "b")
    mu_hat = np.array([-0.10 + 0.0 + 0.20, 0.05 + 0.15 + 0.25]) / 3.0
    assert np.allclose(model.mu_hat, mu_hat)
    assert np.allclose(model.prior, [0.0, 0.0])
    assert model.shrinkage_lambda == 1.0


def test_mean_shrinkage_toward_prior(tiny_returns_path):
    data = load_returns_csv(tiny_returns_path)
    model = data.parametric_model(
        ("a", "b"),
        shrinkage_lambda=shrinkage_lambda_for_market_assumption(MarketAssumption.below_average),
        shrinkage_prior={"a": 0.02, "b": -0.01},
    )
    base = model.mu_after_shrinkage()
    assert np.allclose(base, 0.85 * model.mu_hat + 0.15 * np.array([0.02, -0.01]))


def test_sample_month_returns_shape(tiny_returns_path):
    data = load_returns_csv(tiny_returns_path)
    model = data.parametric_model(("a", "b"))
    rng = np.random.default_rng(0)
    d = model.sample_month_returns(rng)
    assert set(d.keys()) == {"a", "b"}
    assert all(isinstance(v, float) for v in d.values())


def test_shrinkage_lambda_mapping():
    assert shrinkage_lambda_for_market_assumption(MarketAssumption.normal) == 1.0
    assert shrinkage_lambda_for_market_assumption(MarketAssumption.below_average) == 0.85
    assert shrinkage_lambda_for_market_assumption(
        MarketAssumption.significantly_below_average
    ) == 0.70


def test_require_indices_raises(tiny_returns_path):
    data = load_returns_csv(tiny_returns_path)
    data.require_indices({"a"})
    try:
        data.require_indices({"a", "missing"})
    except ValueError as e:
        assert "missing" in str(e)
    else:
        raise AssertionError("expected ValueError")
