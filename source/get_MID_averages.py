
import pandas as pd

INPUT_FILE = "final_performance_report.csv"
OUTPUT_FILE = "final_performance_report_averages.csv"

df = pd.read_csv(INPUT_FILE)

group_columns = [
    "Library",
    "TestID",
    "ClientCount",
    "Interval",
    "Timeout",
    "MsgSize"
]

# Require exactly one row for each MID: 1, 2, and 3
required_mids = {1, 2, 3}

valid_keys = (
    df.groupby(group_columns)["MID"]
      .agg(lambda s: len(s) == 3 and set(s) == required_mids)
)

valid_keys = valid_keys[valid_keys].index

# Keep only complete groups with three runs
df_valid = df.set_index(group_columns).loc[valid_keys].reset_index()

# Average all numeric columns except MID and grouping columns
average_columns = [
    col for col in df_valid.select_dtypes(include="number").columns
    if col not in group_columns and col != "MID"
]

result = (
    df_valid.groupby(group_columns, as_index=False, sort=True)
    [average_columns]
    .mean()
)

# Preserve the original column order, excluding MID
output_columns = [
    col for col in df.columns if col != "MID"
]
result = result[output_columns]

# Save as CSV
result.to_csv(OUTPUT_FILE, index=False, float_format="%.4f")

print("Input rows:", len(df))
print("Complete groups:", len(result))
print("Output columns:", len(result.columns))
print("Output file:", OUTPUT_FILE)

print(result.head())
