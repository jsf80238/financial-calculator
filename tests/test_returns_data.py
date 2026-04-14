from financial_calculator.models import ReturnMethod
from financial_calculator.returns_data import load_returns_csv


def test_load_sort_mean_and_pools(tiny_returns_path):
    data = load_returns_csv(tiny_returns_path)
    a = data.by_name["a"]
    assert a.sorted_change_percents == (-0.10, 0.0, 0.20)
    assert abs(a.mean - (-0.10 + 0.0 + 0.20) / 3.0) < 1e-12

    m = a.mean
    normal = a.pool(ReturnMethod.normal)
    assert normal == [-0.10, 0.0, 0.20]

    below = a.pool(ReturnMethod.below_average)
    assert below == [x - 0.15 * m for x in normal]

    sig = a.pool(ReturnMethod.significantly_below_average)
    assert sig == [x - 0.30 * m for x in normal]


def test_require_indices_raises(tiny_returns_path):
    data = load_returns_csv(tiny_returns_path)
    data.require_indices({"a"})
    try:
        data.require_indices({"a", "missing"})
    except ValueError as e:
        assert "missing" in str(e)
    else:
        raise AssertionError("expected ValueError")
