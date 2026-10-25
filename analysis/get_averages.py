import pandas as pd

# 1. Load the dataset
df = pd.read_csv('final_performance_report.csv')

# 2. Filter rows where MID is 1, 2, or 3
filtered_df = df[df['MID'].isin([1, 2, 3])]

# 3. Define the grouping columns
group_cols = ['Library', 'ClientCount', 'Interval', 'Timeout', 'MsgSize']

# 4. Get averages of all other numeric columns for each group
# numeric_only=True automatically selects all numeric columns (like RTT, Throughput, Conn_Success_%, etc.)
averages_df = filtered_df.groupby(group_cols).mean(numeric_only=True).reset_index()

# 5. Display the first few rows of the result
print(averages_df.head())

# 6. Save the resulting averages to a new CSV file
averages_df.to_csv('final_performance_report_averages.csv', index=False)