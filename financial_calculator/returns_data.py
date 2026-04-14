from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from financial_calculator.models import ReturnMethod


@dataclass(frozen=True)
class IndexReturns:
    """Historical month-over-month returns for one index_name (sorted ascending)."""

    index_name: str
    sorted_change_percents: tuple[float, ...]
    mean: float

    def pool(self, method: ReturnMethod) -> list[float]:
        vals = list(self.sorted_change_percents)
        m = self.mean
        if method is ReturnMethod.normal:
            return vals
        if method is ReturnMethod.below_average:
            return [x - 0.15 * m for x in vals]
        if method is ReturnMethod.significantly_below_average:
            return [x - 0.30 * m for x in vals]
        raise NotImplementedError(method)


@dataclass(frozen=True)
class ReturnsData:
    """All index series loaded from monthly_returns.csv."""

    by_name: dict[str, IndexReturns]
    csv_path: Path

    def require_indices(self, names: set[str]) -> None:
        missing = names - set(self.by_name)
        if missing:
            raise ValueError(
                f"Unknown index_name(s) not in returns data: {sorted(missing)}"
            )


def load_returns_csv(path: Path | str) -> ReturnsData:
    path = Path(path)
    by_name: dict[str, list[float]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"index_name", "change_percent"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"CSV must have columns {required}, got {reader.fieldnames!r}"
            )
        for row in reader:
            name = row["index_name"].strip()
            cp = float(row["change_percent"])
            by_name.setdefault(name, []).append(cp)

    frozen: dict[str, IndexReturns] = {}
    for name, values in by_name.items():
        sorted_vals = tuple(sorted(values))
        mean = sum(sorted_vals) / len(sorted_vals)
        frozen[name] = IndexReturns(
            index_name=name,
            sorted_change_percents=sorted_vals,
            mean=mean,
        )
    return ReturnsData(by_name=frozen, csv_path=path.resolve())
