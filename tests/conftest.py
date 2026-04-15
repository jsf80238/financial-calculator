import pytest


@pytest.fixture
def tiny_returns_path(tmp_path):
    """Two indices with shared end_dates for covariance fitting."""
    p = tmp_path / "monthly_returns.csv"
    p.write_text(
        "index_name,start_date,end_date,period_length,change_percent\n"
        "a,2000-01-31,2000-02-29,month,-0.10\n"
        "a,2000-02-29,2000-03-31,month,0.00\n"
        "a,2000-03-31,2000-04-30,month,0.20\n"
        "b,2000-01-31,2000-02-29,month,0.05\n"
        "b,2000-02-29,2000-03-31,month,0.15\n"
        "b,2000-03-31,2000-04-30,month,0.25\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def zero_returns_path(tmp_path):
    """Aligned zero returns so multivariate draws are ~0."""
    p = tmp_path / "monthly_returns.csv"
    p.write_text(
        "index_name,start_date,end_date,period_length,change_percent\n"
        "a,2000-01-31,2000-02-29,month,0\n"
        "a,2000-02-29,2000-03-31,month,0\n"
        "b,2000-01-31,2000-02-29,month,0\n"
        "b,2000-02-29,2000-03-31,month,0\n",
        encoding="utf-8",
    )
    return p
