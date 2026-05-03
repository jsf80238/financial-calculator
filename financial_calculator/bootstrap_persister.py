from csv import DictReader
import pandas as pd
import os
from pathlib import Path
# Imports above are standard Python
# Imports below are 3rd-party
from base import Logger, RETURNS_PATH
from functools import reduce

logger = Logger().get_logger()
DATE_COLUMN_NAME = 'Date'


def create_master_history(directory_path: Path):
    all_dfs = []

    # 1. Iterate through every CSV in the directory
    for file_path in directory_path.glob("*.csv"):
        asset_name = file_path.stem
        if asset_name == "monthly_returns":
            continue

        # Load the CSV
        # Assuming 'Date' column and the second column is the return
        df = pd.read_csv(file_path)
        df[DATE_COLUMN_NAME] = pd.to_datetime(df[DATE_COLUMN_NAME])

        # Ensure return column is named after the asset
        # We assume the first non-date column is the return
        return_col = [c for c in df.columns if c != DATE_COLUMN_NAME][0]
        df = df[['Date', return_col]].rename(columns={return_col: asset_name})

        all_dfs.append(df)

    # 2. Merge all DataFrames on 'Date' using an Inner Join
    # This automatically keeps only the dates that exist in ALL files
    master_df = reduce(lambda left, right: pd.merge(left, right, on='Date', how='inner'), all_dfs)

    # Set Date as index and sort
    master_df = master_df.sort_values('Date').set_index('Date')

    logger.info(f"Start Date: {master_df.index.min()}")
    logger.info(f"End Date:   {master_df.index.max()}")
    logger.info(f"Total overlapping months: {len(master_df)}")

    return master_df

# Example usage:
# master_history = create_master_history("./my_investment_data")



if __name__ == "__main__":
    returns_df = create_master_history(RETURNS_PATH)
    print(returns_df)
