# Generate a parquet file for each investment type
# Each row is a path, each column is a month

from csv import DictReader
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
from pathlib import Path
# Imports above are standard Python
# Imports below are 3rd-party
from base import Logger, RETURNS_PATH

logger = Logger().get_logger()
YEARS = 50
TOTAL_SIMULATIONS = 100000
CHUNK_SIZE = 10000


def run_fixed_monte_carlo(
        historical_pct_changes: list,
        initial_investment,
        years,
        total_sims,
        chunk_size,
        output_filepath: Path
):
    months = years * 12

    # 1. Fix the "Divide by Zero" / Percentage issue
    data = np.array(historical_pct_changes)
    if np.any(data > 1.0) or np.any(data < -1.0):
        data = data / 100.0  # Convert 5.0 to 0.05

    # Safety clip to prevent log(0) if a -100% exists in data
    data = np.clip(data, -0.9999, None)

    log_returns = np.log(1 + data)
    mu = np.mean(log_returns)
    sigma = np.std(log_returns)

    writer = None
    logger.info(f"Generating {total_sims} simulations in chunks of {chunk_size}...")

    for i in range(0, total_sims, chunk_size):
        current_chunk = min(chunk_size, total_sims - i)

        # 2. Generate GBM for the chunk
        # Note the shape: (Simulations, Months)
        z = np.random.standard_normal((current_chunk, months))
        drift = mu - 0.5 * sigma ** 2

        # Monthly growth paths
        # We prepend a column of zeros for Month 0
        periodic_growth = drift + (sigma * z)
        zeros = np.zeros((current_chunk, 1))
        cumulative_growth = np.cumsum(np.hstack([zeros, periodic_growth]), axis=1)

        paths = initial_investment * np.exp(cumulative_growth)

        # 3. Create DataFrame (Rows = Simulations, Columns = Months)
        # Column names: "M000", "M001", etc.
        col_names = [f"M{m:03d}" for m in range(months + 1)]
        df_chunk = pd.DataFrame(paths, columns=col_names, dtype='float32')

        # 4. Append to Parquet
        table = pa.Table.from_pandas(df_chunk)
        if writer is None:
            # The schema is defined by the first chunk (M000 to M600)
            writer = pq.ParquetWriter(output_filepath, table.schema, compression='snappy')

        writer.write_table(table)
        logger.info(f"Saved simulations {i} to {i + current_chunk}...")

    if writer:
        writer.close()
    logger.info(f"Wrote {os.stat(output_filepath).st_size} bytes to {output_filepath}")


if __name__ == "__main__":
    RETURNS_DATA = RETURNS_PATH / "monthly_returns.csv"
    for index in sorted(RETURNS_PATH.glob("*.csv")):
        index_name = index.stem
        if index_name == "monthly_returns":
            continue
        logger.info(f"Working on index '{index_name}' ...")
        with open(RETURNS_DATA, "r", newline="") as f:
            reader = DictReader(f)
            historical_data = [float(row["change_percent"]) for row in reader if row["index_name"] == index_name]
            # historical_data = np.random.normal(0.007, 0.04, 360)  # Placeholder for your list
            # print(min(historical_data))
            # exit()

            run_fixed_monte_carlo(
                historical_pct_changes=historical_data,
                initial_investment=100,
                years=YEARS,
                total_sims=TOTAL_SIMULATIONS,
                chunk_size=CHUNK_SIZE,
                output_filepath=RETURNS_PATH / (index_name+".parquet")
            )