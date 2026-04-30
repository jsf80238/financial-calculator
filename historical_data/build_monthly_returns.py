#!/usr/bin/env python3
"""
Read index CSV files (date + price per row) and emit one CSV of month-period
returns: index_name, start_date, end_date, period_length, change_percent.

Only month-end to month-end periods: start_date is the last calendar day of
month M and end_date is the last calendar day of month M+1. Both dates must
exist exactly in the input (no nearest-trading-day fallback).
"""

import argparse
import calendar
import csv
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
# Imports above are standard Python
# Imports below are 3rd-party
from dateutil import relativedelta


def parse_date(s: str) -> date:
    s = s.strip()
    return datetime.strptime(s, "%Y-%m-%d").date()


def try_float(s: str) -> float | None:
    try:
        return float(s.strip())
    except (TypeError, ValueError):
        return None


def last_calendar_day_of_month(year: int, month: int) -> date:
    day = calendar.monthrange(year, month)[1]
    return date(year, month, day)


def last_calendar_day_of_next_month(d: date) -> date:
    """d must be the last calendar day of its month."""
    if d.month == 12:
        return last_calendar_day_of_month(d.year + 1, 1)
    return last_calendar_day_of_month(d.year, d.month + 1)


def is_last_calendar_day_of_month(d: date) -> bool:
    return d.day == calendar.monthrange(d.year, d.month)[1]


def load_series(path: Path) -> list[tuple[date, float]]:
    rows: list[tuple[date, float]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            p = try_float(row[1])
            if p is None:
                continue
            try:
                d = parse_date(row[0])
            except ValueError:
                continue
            rows.append((d, p))
    rows.sort(key=lambda x: x[0])
    merged: dict[date, float] = {}
    for d, p in rows:
        merged[d] = p
    return [(d, merged[d]) for d in sorted(merged)]


def month_period_returns(series: list[tuple[date, float]]) -> list[tuple[date, date, float]]:
    if not series:
        return []
    price = {d: p for d, p in series}
    out: list[tuple[date, date, float]] = []
    for start_date in sorted(price):
        if not is_last_calendar_day_of_month(start_date):
            continue
        end_date = last_calendar_day_of_next_month(start_date)
        if end_date not in price:
            continue
        start_px = price[start_date]
        end_px = price[end_date]
        if start_px == 0:
            continue
        change = round(end_px / start_px - 1.0, 4)
        out.append((start_date, end_date, change))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build combined month-period return CSV from index CSV files."
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=".",
        type=Path,
        help="Directory containing index CSV files (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: <input_dir>/monthly_returns.csv)",
    )
    args = parser.parse_args()
    input_dir: Path = args.input_dir.resolve()
    out_path = args.output if args.output is not None else input_dir / "monthly_returns.csv"

    csv_paths = sorted(input_dir.glob("*.csv"))
    # Exclude our own output if it lives in the same folder
    csv_paths = [p for p in csv_paths if p.resolve() != out_path.resolve()]

    if not csv_paths:
        print(f"No CSV files found in {input_dir}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as outf:
        w = csv.writer(outf)
        w.writerow(
            ["index_name", "start_date", "end_date", "period_length", "change_percent"]
        )
        for path in csv_paths:
            index_name = path.stem
            series = load_series(path)
            # Data for T-bills/interest bearing is in a straight yearly percentage
            # They will be named something like "3month" or "7day"
            if index_name[0].isdigit():
                for row in load_series(path):
                    start_date = row[0]
                    if start_date.day != 1:
                        continue
                    end_date = start_date + relativedelta.relativedelta(months=+1)
                    change = row[1] / 12  # Original is a yearly rate
                    w.writerow(
                        [
                            index_name,
                            start_date.isoformat(),  # start_date
                            end_date.isoformat(),
                            "month",
                            f"{change:.4f}",
                        ]
                    )
            else:  # Other data is prices, so need to calculate the monthly difference
                for start_date, end_date, change in month_period_returns(series):
                    w.writerow(
                        [
                            index_name,
                            start_date.isoformat(),
                            end_date.isoformat(),
                            "month",
                            f"{change:.4f}",
                        ]
                    )

    print(f"Wrote {os.stat(out_path).st_size} bytes to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
