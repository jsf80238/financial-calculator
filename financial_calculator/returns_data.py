from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.random import Generator


@dataclass(frozen=True)
class IndexSeries:
    """Monthly returns keyed by end_date (ISO string), from monthly_returns.csv."""

    index_name: str
    by_end_date: dict[str, float]

    def marginal_mean(self) -> float:
        vals = list(self.by_end_date.values())
        return float(sum(vals) / len(vals)) if vals else 0.0

    def marginal_var(self) -> float:
        vals = np.array(list(self.by_end_date.values()), dtype=float)
        if len(vals) < 2:
            return 0.0
        return float(np.var(vals, ddof=1))


@dataclass(frozen=True)
class ParametricReturnModel:
    """
    Multivariate Normal model for one month of returns across ``indices``.

    Fitted on calendar rows where every index in ``indices`` has the same
    ``end_date``. If fewer than two aligned months exist, covariance falls back
    to diagonal marginal sample variances per index.

    The mean vector uses **shrinkage only** (no extra pessimistic scaling):
    ``μ = λ μ̂ + (1−λ) μ_prior`` where ``λ`` comes from ``--market-assumption``.
    """

    indices: tuple[str, ...]
    mu_hat: np.ndarray
    prior: np.ndarray
    shrinkage_lambda: float
    sigma: np.ndarray

    def mu_after_shrinkage(self) -> np.ndarray:
        lam = float(self.shrinkage_lambda)
        return lam * self.mu_hat + (1.0 - lam) * self.prior

    def sample_month_returns(self, rng: Generator) -> dict[str, float]:
        mu_adj = self.mu_after_shrinkage()
        if np.allclose(self.sigma, 0.0, atol=1e-14):
            return {name: float(mu_adj[j]) for j, name in enumerate(self.indices)}
        sigma = _ensure_psd(self.sigma)
        x = rng.multivariate_normal(mean=mu_adj, cov=sigma)
        return {name: float(x[j]) for j, name in enumerate(self.indices)}


def _ensure_psd(sigma: np.ndarray, eps: float = 1e-10) -> np.ndarray:
    """Symmetric positive semi-definite -> strictly PD for sampling."""
    sigma = (sigma + sigma.T) / 2.0
    w, v = np.linalg.eigh(sigma)
    w = np.maximum(w, eps)
    return (v * w) @ v.T


def _fit_parametric_model(
    data: "ReturnsData", indices: tuple[str, ...]
) -> tuple[np.ndarray, np.ndarray]:
    if not indices:
        raise ValueError("indices must be non-empty")

    end_sets = [set(data.by_name[i].by_end_date) for i in indices]
    common = set.intersection(*end_sets)
    sorted_dates = sorted(common)
    k = len(indices)
    n = len(sorted_dates)

    if n == 0:
        raise ValueError(
            f"No common end_date across indices {indices!r}; cannot estimate covariance"
        )

    x = np.zeros((n, k), dtype=float)
    for j, name in enumerate(indices):
        col = data.by_name[name].by_end_date
        for i, d in enumerate(sorted_dates):
            x[i, j] = col[d]

    mu_hat = np.mean(x, axis=0)

    if n >= 2:
        sigma = np.cov(x, rowvar=False, ddof=1)
        if sigma.ndim == 0:
            sigma = np.array([[float(sigma)]])
        elif sigma.shape == (k,):
            sigma = np.diag(sigma)
    else:
        vars_ = np.array([data.by_name[name].marginal_var() for name in indices], dtype=float)
        sigma = np.diag(np.maximum(vars_, 1e-12))

    return mu_hat.astype(float), sigma.astype(float)


def _prior_vector(
    indices: tuple[str, ...], shrinkage_prior: dict[str, float] | None
) -> np.ndarray:
    pri = shrinkage_prior or {}
    return np.array([float(pri.get(name, 0.0)) for name in indices], dtype=float)


@dataclass(frozen=True)
class ReturnsData:
    """Historical monthly returns from monthly_returns.csv (parametric fitting)."""

    by_name: dict[str, IndexSeries]
    csv_path: Path

    def require_indices(self, names: set[str]) -> None:
        missing = names - set(self.by_name)
        if missing:
            raise ValueError(
                f"Unknown index_name(s) not in returns data: {sorted(missing)}"
            )

    def parametric_model(
        self,
        indices: tuple[str, ...],
        *,
        shrinkage_lambda: float = 1.0,
        shrinkage_prior: dict[str, float] | None = None,
    ) -> ParametricReturnModel:
        """Indices in stable order (caller should pass a sorted tuple)."""
        self.require_indices(set(indices))
        mu_hat, sigma = _fit_parametric_model(self, indices)
        prior = _prior_vector(indices, shrinkage_prior)
        return ParametricReturnModel(
            indices=indices,
            mu_hat=mu_hat,
            prior=prior,
            shrinkage_lambda=float(shrinkage_lambda),
            sigma=sigma,
        )


def load_returns_csv(path: Path | str) -> ReturnsData:
    path = Path(path)
    by_name: dict[str, dict[str, float]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"index_name", "end_date", "change_percent"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"CSV must have columns {required}, got {reader.fieldnames!r}"
            )
        for row in reader:
            name = row["index_name"].strip()
            end = row["end_date"].strip()
            cp = float(row["change_percent"])
            by_name.setdefault(name, {})[end] = cp

    frozen = {
        name: IndexSeries(index_name=name, by_end_date=dates)
        for name, dates in by_name.items()
    }
    return ReturnsData(by_name=frozen, csv_path=path.resolve())
