from datetime import datetime, date
import pyarrow.parquet as pq
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
# Imports above are standard Python
# Imports below are 3rd-party
from base import Logger, RETURNS_PATH
from dateutil import relativedelta


logger = Logger().get_logger()


def get_random_path(index_name: str):
    # 1. Open the Parquet file (metadata only)
    filepath = RETURNS_PATH / f"{index_name}.parquet"
    pfile = pq.ParquetFile(filepath)

    # 2. Pick a random row group
    # Since we saved in chunks of 100k, there are 10 groups in 1M sims
    num_groups = pfile.num_row_groups
    random_group_idx = np.random.randint(0, num_groups)

    logger.debug(f"Reading from row group {random_group_idx} of {num_groups}...")

    # 3. Load only that specific row group into a DataFrame
    table = pfile.read_row_group(random_group_idx)
    df_chunk = table.to_pandas()

    # 4. Pick one random row (simulation) from this chunk
    random_sim = df_chunk.sample(n=1)

    # Convert to a Series for easier plotting (transpose so index is Month)
    path_series = random_sim.iloc[0]
    path_series.index = [int(m[1:]) for m in path_series.index]  # Convert 'M001' to 1

    return path_series


if __name__ == "__main__":
    # --- Execution ---
    index_name = "sp500"

    max = 0
    min = 9999999999
    for i in range(1):
        # Pull a random "journey"
        single_path = get_random_path(index_name)
        # month = date.today().replace(day=1)
        # for i, result in enumerate(single_path.to_list()):
        #     month += relativedelta.relativedelta(months=+1)
            # print(month.isoformat(), result)

        # --- Visualize the Journey ---
        plt.plot(single_path)
        plt.figure(figsize=(10, 6))
        plt.title(f"Random {index_name} Simulation (50 Years)")
        plt.xlabel("Month")
        plt.ylabel("Investment Value ($)")
        plt.grid(True, alpha=0.3)
        plt.show()
        final_value = single_path.iloc[-1]
        if final_value > max:
            max = final_value
        if final_value < min:
            min = final_value
        # logger.info(f"Final Value after 50 years: ${final_value:,.2f}")
    logger.info(f"Min: {min}, Max: {max}")