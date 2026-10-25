import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# SETTINGS
# ============================================================

FILE = "final_performance_report.csv"

# Experimental factors that define one identical configuration
CONFIG_COLS = [
    "Library",
    "TestID",
    "ClientCount",
    "Interval",
    "Timeout",
    "MsgSize"
]

VALUE_COL = "Avg_RTT_ms"

# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(FILE)

# Keep only MID 1, 2, 3
df = df[df["MID"].isin([1, 2, 3])].copy()

# Make sure values are numeric
df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")

# ============================================================
# 1. CHECK THAT EACH CONFIGURATION HAS 3 MEASUREMENTS
# ============================================================

check = (
    df.groupby(CONFIG_COLS)["MID"]
      .nunique()
      .reset_index(name="MID_count")
)

print("\nConfigurations with all 3 MIDs:")
print((check["MID_count"] == 3).sum())

print("\nConfigurations with missing MIDs:")
print((check["MID_count"] < 3).sum())

# ============================================================
# 2. PIVOT MID 1, 2, 3
# ============================================================

wide = (
    df.pivot_table(
        index=CONFIG_COLS,
        columns="MID",
        values=VALUE_COL,
        aggfunc="mean"
    )
    .reset_index()
)

wide = wide.rename(columns={
    1: "MID1",
    2: "MID2",
    3: "MID3"
})

# Only complete triplets
wide = wide.dropna(subset=["MID1", "MID2", "MID3"])

print("\nNumber of complete experimental configurations:", len(wide))

# ============================================================
# 3. VARIABILITY ACROSS MID 1, 2, 3
# ============================================================

mid_values = wide[["MID1", "MID2", "MID3"]]

wide["MID_Mean"] = mid_values.mean(axis=1)
wide["MID_SD"] = mid_values.std(axis=1, ddof=1)

wide["MID_Min"] = mid_values.min(axis=1)
wide["MID_Max"] = mid_values.max(axis=1)

wide["MID_Range"] = wide["MID_Max"] - wide["MID_Min"]

# Coefficient of variation
wide["MID_CV_%"] = (
    wide["MID_SD"] / wide["MID_Mean"]
) * 100

print("\n===================================================")
print("VARIABILITY OF Avg_RTT_ms ACROSS MID 1, 2, 3")
print("===================================================")

print(
    wide[
        [
            "MID_Mean",
            "MID_SD",
            "MID_Range",
            "MID_CV_%"
        ]
    ].describe()
)

# ============================================================
# 4. PAIRED EFFECT SIZE: COHEN'S dz
# ============================================================

def paired_cohens_dz(x, y):
    """
    Cohen's dz for paired observations.

    dz = mean(x-y) / SD(x-y)
    """

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    diff = x - y

    sd_diff = np.std(diff, ddof=1)

    if sd_diff == 0:
        return np.nan

    return np.mean(diff) / sd_diff


comparisons = {
    "MID1 vs MID2": ("MID1", "MID2"),
    "MID1 vs MID3": ("MID1", "MID3"),
    "MID2 vs MID3": ("MID2", "MID3")
}

effect_results = []

for name, (a, b) in comparisons.items():

    x = wide[a].values
    y = wide[b].values

    diff = x - y

    dz = paired_cohens_dz(x, y)

    effect_results.append({
        "Comparison": name,
        "N": len(diff),
        "Mean_Difference_ms": np.mean(diff),
        "SD_Difference_ms": np.std(diff, ddof=1),
        "Cohen_dz": dz,
        "Mean_Absolute_Difference_ms": np.mean(np.abs(diff)),
        "Median_Absolute_Difference_ms": np.median(np.abs(diff))
    })

effect_df = pd.DataFrame(effect_results)

print("\n===================================================")
print("PAIRED EFFECT SIZES")
print("===================================================")

print(effect_df.to_string(index=False))

# ============================================================
# 5. INTERPRET COHEN'S dz
# ============================================================

def interpret_effect(d):
    d = abs(d)

    if d < 0.2:
        return "Negligible"
    elif d < 0.5:
        return "Small"
    elif d < 0.8:
        return "Medium"
    else:
        return "Large"


effect_df["Effect"] = effect_df["Cohen_dz"].apply(interpret_effect)

print("\nEffect-size interpretation:")
print(
    effect_df[
        ["Comparison", "Cohen_dz", "Effect"]
    ].to_string(index=False)
)

# ============================================================
# 6. EFFECT SIZE FOR EACH LIBRARY
# ============================================================

library_effects = []

for library, g in wide.groupby("Library"):

    for name, (a, b) in comparisons.items():

        x = g[a].values
        y = g[b].values

        dz = paired_cohens_dz(x, y)

        library_effects.append({
            "Library": library,
            "Comparison": name,
            "N": len(g),
            "Cohen_dz": dz,
            "Mean_Difference_ms": np.mean(x - y)
        })

library_effects = pd.DataFrame(library_effects)

print("\n===================================================")
print("EFFECT SIZE BY LIBRARY")
print("===================================================")

print(library_effects.to_string(index=False))

# ============================================================
# 7. PLOT 1: AVG RTT FOR MID 1, 2, 3
# ============================================================

plt.figure(figsize=(9, 6))

data = [
    wide["MID1"],
    wide["MID2"],
    wide["MID3"]
]

plt.boxplot(
    data,
    label=["MID 1", "MID 2", "MID 3"],
    showmeans=True
)

plt.ylabel("Avg RTT (ms)")
plt.xlabel("Measurement ID")
plt.title("Variability of Avg RTT Across MID 1–3")
plt.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.show()

# ============================================================
# 8. PLOT 2: COEFFICIENT OF VARIATION
# ============================================================

plt.figure(figsize=(10, 6))

plt.hist(
    wide["MID_CV_%"],
    bins=40
)

plt.axvline(
    wide["MID_CV_%"].median(),
    linestyle="--",
    label=f"Median CV = {wide['MID_CV_%'].median():.2f}%"
)

plt.xlabel("Coefficient of Variation (%)")
plt.ylabel("Number of Configurations")
plt.title("Variability of Avg RTT Across MID 1–3")

plt.legend()
plt.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.show()

# ============================================================
# 9. PLOT 3: EFFECT SIZE DISTRIBUTION
# ============================================================

plt.figure(figsize=(10, 6))

effect_distributions = []

labels = []

for name, (a, b) in comparisons.items():

    differences = wide[a] - wide[b]

    # Paired Cohen's dz for individual library/configuration
    # distribution is better represented by standardized
    # differences across configurations.

    pooled_sd = np.std(
        np.column_stack([wide[a], wide[b]]),
        axis=1,
        ddof=1
    )

    # Standardized paired difference
    d_individual = differences / pooled_sd
 
    effect_distributions.append(d_individual.dropna())
    labels.append(name)

plt.boxplot(
    effect_distributions,
    tick_labels=labels,
    showmeans=True
)

plt.axhline(
    0,
    linestyle="--"
)

plt.ylabel("Standardized Difference")
plt.xlabel("MID Comparison")
plt.title("Effect Size Distribution of Avg RTT")

plt.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.show()

# ============================================================
# 10. PLOT 4: COHEN'S dz BY LIBRARY
# ============================================================

pivot_effect = library_effects.pivot(
    index="Library",
    columns="Comparison",
    values="Cohen_dz"
)

pivot_effect.plot(
    kind="bar",
    figsize=(12, 6)
)

plt.axhline(
    0,
    linestyle="--"
)

plt.ylabel("Paired Cohen's dz")
plt.xlabel("WebSocket Library")
plt.title("Effect Sizes Between Repeated Measurements")

plt.xticks(rotation=30, ha="right")
plt.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.show()

# ============================================================
# 11. SUMMARY TABLE BY LIBRARY
# ============================================================

variability_by_library = (
    wide.groupby("Library")
    .agg(
        Mean_Avg_RTT_ms=("MID_Mean", "mean"),
        SD_Across_MID_ms=("MID_SD", "mean"),
        Median_CV_percent=("MID_CV_%", "median"),
        Mean_Range_ms=("MID_Range", "mean")
    )
    .reset_index()
)

print("\n===================================================")
print("VARIABILITY SUMMARY BY LIBRARY")
print("===================================================")

print(
    variability_by_library.to_string(index=False)
)

# ============================================================
# 12. SAVE RESULTS
# ============================================================

wide.to_csv(
    "MID_variability_results.csv",
    index=False
)

effect_df.to_csv(
    "MID_overall_effect_sizes.csv",
    index=False
)

library_effects.to_csv(
    "MID_library_effect_sizes.csv",
    index=False
)

variability_by_library.to_csv(
    "MID_library_variability.csv",
    index=False
)

print("\nResults saved:")
print("  MID_variability_results.csv")
print("  MID_overall_effect_sizes.csv")
print("  MID_library_effect_sizes.csv")
print("  MID_library_variability.csv")