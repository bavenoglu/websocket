import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

# 1. Load dataset
df = pd.read_csv("final_performance_report.csv")

# 2. Group strictly by ClientCount, Interval, and MID (averaging across all libraries, message sizes, and timeouts)
agg_all = (
    df.groupby(["ClientCount", "Interval", "MID"])
    .agg(
        Avg_RTT=("Avg_RTT_ms", "mean"),
        Median_RTT=("Median_RTT_ms", "mean"),
        Std_RTT=("Std_RTT_ms", "mean"),
        P95=("P95_RTT_ms", "mean"),
        P95_Lower=("P95_CI95_Lower_ms", "mean"),
        P95_Upper=("P95_CI95_Upper_ms", "mean"),
    )
    .reset_index()
)

intervals = sorted(agg_all["Interval"].unique())
client_counts = sorted(agg_all["ClientCount"].unique())
mids = sorted(agg_all["MID"].unique())

# 3. Initialize multi-panel grid: Rows = Intervals, Cols = 1
fig, axes = plt.subplots(len(intervals), 1, figsize=(12, 14), sharex=True)

mid_colors = {1: "#3498db", 2: "#2ecc71", 3: "#c1da34"}

# Custom Legend Elements
legend_elements = [
    plt.Rectangle((0, 0), 1, 1, color="#3498db", label="Run 1 RTT Avg "),
    plt.Rectangle((0, 0), 1, 1, color="#2ecc71", label="Run 2 RTT Avg"),
    plt.Rectangle((0, 0), 1, 1, color="#c1da34", label="Run 3 RTT Avg"),
    Line2D(
        [0],
        [0],
        marker="o",
        color="w",
        markerfacecolor="purple",
        markersize=7,
        label="RTT Median",
    ),
    Line2D(
        [0],
        [0],
        marker="^",
        color="w",
        markerfacecolor="crimson",
        markersize=7,
        label="RTT Std. Dev.",
    ),
    Line2D(
        [0], [0], color="darkorange", lw=2, label="P95 Conf. Intervals"
    ),
]

# 4. Loop through each Interval row
for idx, interval in enumerate(intervals):
  ax = axes[idx]
  sub_interval = agg_all[agg_all["Interval"] == interval]

  x = np.arange(len(client_counts))
  width = 0.25

  for i, mid in enumerate(mids):
    mid_data = sub_interval[sub_interval["MID"] == mid]
    bar_x = x + (i - 1) * width

    # Avg RTT bars
    ax.bar(
        bar_x,
        mid_data["Avg_RTT"],
        width,
        color=mid_colors[mid],
        alpha=0.85,
    )

    # P95 CI Whiskers
    p95_err = [
        mid_data["P95_Lower"], # mid_data["P95"] - mid_data["P95_Lower"],
        mid_data["P95_Upper"] # - mid_data["P95"],
    ]
    ax.errorbar(
        bar_x,
        mid_data["P95"],
        yerr=p95_err,
        fmt="none",
        ecolor="darkorange",
        elinewidth=1.5,
        capsize=2,
    )

    # Median and Std markers
    ax.scatter(
        bar_x, mid_data["Median_RTT"], color="purple", marker="o", s=25, zorder=5
    )
    ax.scatter(
        bar_x, mid_data["Std_RTT"], color="crimson", marker="^", s=25, zorder=5
    )

  # Subplot styling with logarithmic scale
  ax.set_title(
      f"Interval = {interval} ms", fontsize=11, fontweight="bold", pad=6
  )
  ax.set_ylabel("RTT (ms) [Log Scale]", fontsize=10)
  ax.set_yscale("log")  # Logarithmic scale for clarity across wide ranges

  ax.set_xticks(x)
  ax.set_xticklabels(client_counts, fontsize=9)
  ax.grid(True, which="both", linestyle="--", alpha=0.5)

# 5. Global Layout and Formatting
axes[-1].set_xlabel("Client Count", fontsize=11, labelpad=8)
fig.suptitle(
    "Overall RTT Performance across Intervals & Client Counts\n(Averaged across All Libraries, Message Sizes, and Timeouts)",
    fontsize=14,
    y=0.98,
)

fig.legend(
    handles=legend_elements,
    loc="upper right",
    bbox_to_anchor=(0.98, 1),
    fontsize=9,
)
plt.tight_layout(rect=[0, 0, 1, 0.95])

# Save and show
plt.savefig("runvariability.png", dpi=300)
plt.show()