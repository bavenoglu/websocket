
import pandas as pd
import numpy as np
from itertools import combinations

# --------------------------------------------------
# Load data
# --------------------------------------------------
df = pd.read_csv("final_performance_report_averages.csv")

metric = "Avg_RTT_ms"

# Each row represents one workload configuration
config_cols = [
    "ClientCount",
    "Interval",
    "Timeout",
    "MsgSize"
]

# --------------------------------------------------
# Create paired RTT observations
# --------------------------------------------------
pivot = df.pivot_table(
    index=config_cols,
    columns="Library",
    values=metric,
    aggfunc="mean"
)

libraries = pivot.columns.tolist()

# --------------------------------------------------
# Calculate paired Cohen's dz
# --------------------------------------------------
results = []

for lib1, lib2 in combinations(libraries, 2):

    # Matched workload configurations
    paired = pivot[[lib1, lib2]].dropna()

    x = paired[lib1].values
    y = paired[lib2].values

    differences = x - y

    mean_diff = np.mean(differences)
    sd_diff = np.std(differences, ddof=1)

    # Paired Cohen's d (Cohen's dz)
    dz = mean_diff / sd_diff if sd_diff > 0 else np.nan

    results.append({
        "Library 1": lib1,
        "Library 2": lib2,
        "N": len(differences),
        "Mean RTT Difference (ms)": mean_diff,
        "Cohen's dz": dz,
        "Absolute dz": abs(dz)
    })

pairwise = pd.DataFrame(results)

# --------------------------------------------------
# Library-level effect size summary
# --------------------------------------------------
summary = pd.concat([
    pairwise.groupby("Library 1")["Absolute dz"].mean(),
    pairwise.groupby("Library 2")["Absolute dz"].mean()
]).groupby(level=0).mean()

library_effects = summary.rename(
    "Mean Absolute Pairwise Cohen's dz"
).reset_index()

library_effects = library_effects.sort_values(
    "Mean Absolute Pairwise Cohen's dz",
    ascending=False
)

# --------------------------------------------------
# Print results
# --------------------------------------------------
print("\n=== Pairwise Cohen's dz ===")
print(pairwise.to_string(index=False))

print("\n=== Library Effect Size Summary ===")
print(library_effects.to_string(index=False))

# Save results
pairwise.to_csv("pairwise_cohens_dz.csv", index=False)
library_effects.to_csv("library_effect_sizes.csv", index=False)
