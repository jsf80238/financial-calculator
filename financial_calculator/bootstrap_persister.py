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
OUTPUT_FILE = Path(RETURNS_PATH / 'master_history.csv')


def create_master_history(directory_path: Path):
    all_dfs = []

    # Iterate through every CSV in the directory
    for file_path in directory_path.glob("*.csv"):
        asset_name = file_path.stem
        if asset_name in ("monthly_returns", OUTPUT_FILE.stem):
            continue

        # Load the CSV
        # Assuming 'Date' column and the second column is the return
        df = pd.read_csv(file_path)
        df.columns = [c.strip() for c in df.columns]
        df[DATE_COLUMN_NAME] = pd.to_datetime(df[DATE_COLUMN_NAME])

        # Identify the data column
        data_col = [c for c in df.columns if c.lower() != DATE_COLUMN_NAME.lower()][0]

        if asset_name == '3month':
            # --- CASE 1: The Yield File ---
            # We assume this is an annual percentage (e.g., 3.5 for 3.5%)
            # Convert annual yield to a monthly decimal return: (Yield / 100) / 12
            df[asset_name] = (df[data_col] / 100) / 12
        else:
            # --- CASE 2: Price Files ---
            # Round prices to two decimals as requested
            df[asset_name] = df[data_col].round(2)
        df = df[[DATE_COLUMN_NAME, asset_name]]
        all_dfs.append(df)

    # Merge all DataFrames on 'Date' using an Inner Join
    # This automatically keeps only the dates that exist in ALL files
    master_df = reduce(lambda left, right: pd.merge(left, right, on='Date', how='inner'), all_dfs)

    # Set Date as index and sort
    master_df = master_df.sort_values('Date').set_index('Date')
    # Sort columns alphabetically (excluding 'Date' which is the index)
    master_df = master_df.reindex(sorted(master_df.columns), axis=1)

    logger.info(f"Start Date: {master_df.index.min()}")
    logger.info(f"End Date:   {master_df.index.max()}")

    # Calculate percentage changes ONLY for the price columns
    # We leave '3month' alone because it's already a return
    price_assets = [c for c in master_df.columns if c != '3month']

    # Calculate returns for price assets
    master_returns = master_df.copy()
    master_returns[price_assets] = master_df[price_assets].pct_change()

    # Drop the first row (NaNs from pct_change)
    master_returns = master_returns.dropna()
    # Round to 7 places
    master_returns = master_returns.round(6)

    return master_returns


if __name__ == "__main__":
    returns_df = create_master_history(RETURNS_PATH)
    target_file = RETURNS_PATH / "master_history.csv"
    returns_df.to_csv(target_file)
    logger.info(f"Wrote {os.stat(target_file).st_size:,d} bytes to {target_file}.")
