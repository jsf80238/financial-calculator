import pandas as pd
import sys
from pathlib import Path

# Load the data
input_file = Path(sys.argv[1])
if not input_file.exists():
    raise FileNotFoundError(input_file)
output_file = input_file.parent / (input_file.stem + "_filled" + input_file.suffix)

df = pd.read_csv(sys.argv[1])

# Convert the Date column to datetime objects
df['Date'] = pd.to_datetime(df['Date'])

# Sort and set Date as the index
df = df.sort_values('Date').set_index('Date')

# Create a full daily date range from the start to the end of the file
full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')

# Reindex the dataframe to include all missing days (creates NaNs for gaps)
df_reindexed = df.reindex(full_range)

# Use linear interpolation to fill the missing prices
# This matches your example: if Day 1 is $10 and Day 3 is $14, Day 2 becomes $12
df_final = df_reindexed.interpolate(method='linear')

# Reset the index to make Date a column again
df_final = df_final.reset_index().rename(columns={'index': 'Date'})

# Save the result to a new CSV
df_final.to_csv(output_file, index=False)

print(f"New file '{output_file}' has been created.")
