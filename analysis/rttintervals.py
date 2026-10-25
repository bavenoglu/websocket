import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

# ============================================================
# Configuration
# ============================================================
INPUT_FILE = "final_performance_report.csv"
OUTPUT_FILE = "rttdist_with_p99_ci.png"

VALUE_COLUMN = "Avg_RTT_ms"
P99_COLUMN = "P99_RTT_ms"
LOWER_COLUMN = "P99_CI95_Lower_ms"
UPPER_COLUMN = "P99_CI95_Upper_ms"

library_order = [
    "Java-WebSocket",
    "Java-Netty",
    "Node-ws",
    "node.js-uws",
    "PHP-Swoole",
    "go",
    "Python-websockets",
]

library_labels = {
    "Java-WebSocket": "Java-WebSocket",
    "Java-Netty": "Java-Netty",
    "Node-ws": "Node.js-ws",
    "node.js-uws": "Node.js-\u00b5WebSockets",
    "PHP-Swoole": "PHP-Swoole",
    "go": "Go-gorilla",
    "Python-websockets": "Python-websockets",
}

palette = {
    "Java-WebSocket": "#287FB5",
    "Java-Netty": "#FF800D",
    "Node-ws": "#D9272E",
    "node.js-uws": "#945B50",
    "PHP-Swoole": "#D96BB5",
    "go": "#B5BE20",
    "Python-websockets": "#19B8C7",
}

# ============================================================
# Read and validate data
# ============================================================
df = pd.read_csv(INPUT_FILE)

required_columns = [
    "MID",
    "Library",
    "Interval",
    "ClientCount",
    VALUE_COLUMN,
    P99_COLUMN,
    LOWER_COLUMN,
    UPPER_COLUMN,
]

missing = set(required_columns) - set(df.columns)

if missing:
  raise ValueError(f"Missing columns in CSV: {sorted(missing)}")

numeric_columns = [
    "Interval",
    "ClientCount",
    VALUE_COLUMN,
    P99_COLUMN,
    LOWER_COLUMN,
    UPPER_COLUMN,
]

for col in numeric_columns:
  df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=required_columns)

# Positive values are required for a logarithmic y-axis.
df = df[
    (df[VALUE_COLUMN] > 0)
    & (df[P99_COLUMN] > 0)
    & (df[LOWER_COLUMN] > 0)
    & (df[UPPER_COLUMN] >= df[LOWER_COLUMN])
    & (df[P99_COLUMN] >= df[LOWER_COLUMN])
    & (df[P99_COLUMN] <= df[UPPER_COLUMN])
].copy()

if df.empty:
  raise ValueError("No valid data remains after filtering.")

# ============================================================
# Plot style
# ============================================================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.titlesize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 300,
})

intervals = sorted(df["Interval"].unique())
client_order = sorted(df["ClientCount"].unique())

fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharey=True)

axes = axes.flatten()
n_libraries = len(library_order)

# Width and horizontal offsets for grouped boxes.
box_width = 0.8
offsets = (
    np.arange(n_libraries) - (n_libraries - 1) / 2
) * (box_width / n_libraries)

# ============================================================
# Draw boxplots and P99 confidence intervals
# ============================================================
for i, interval in enumerate(intervals):
  ax = axes[i]

  subset = df[df["Interval"] == interval].copy()

  # Distribution of average RTT across MID runs.
  sns.boxplot(
      data=subset,
      x="ClientCount",
      y=VALUE_COLUMN,
      order=client_order,
      hue="Library",
      hue_order=library_order,
      palette=palette,
      ax=ax,
      fliersize=2,
      linewidth=0.6,
      notch=False,
      width=box_width,
  )

  # Overlay P99 diamond markers and their 95% CIs.
  for j, library in enumerate(library_order):
    lib_data = subset[subset["Library"] == library]

    # Summarize the supplied per-row values by configuration.
    summary = (
        lib_data.groupby("ClientCount", as_index=False)
        .agg(
            p99=(P99_COLUMN, "mean"),
            lower=(LOWER_COLUMN, "mean"),
            upper=(UPPER_COLUMN, "mean"),
        )
    )

    if summary.empty:
      continue

    x_positions = np.array(
        [client_order.index(c) + offsets[j] for c in summary["ClientCount"]]
    )

    y = summary["p99"].to_numpy()
    lower = summary["lower"].to_numpy()
    upper = summary["upper"].to_numpy()

    # Error bars must be nonnegative.
    valid = (
        np.isfinite(y)
        & np.isfinite(lower)
        & np.isfinite(upper)
        & (y > 0)
        & (lower > 0)
        & (lower <= y)
        & (y <= upper)
    )

    if not np.any(valid):
      continue

    ax.errorbar(
        x_positions[valid],
        y[valid],
        yerr=np.vstack([y[valid] - lower[valid], upper[valid] - y[valid]]),
        fmt="D",
        markersize=3.5,
        color=palette[library],
        ecolor=palette[library],
        elinewidth=0.9,
        capsize=2,
        markeredgecolor="black",
        markeredgewidth=0.3,
        zorder=5,
    )

  # Logarithmic RTT axis.
  ax.set_yscale("log")

  ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:g}"))

  ax.set_xticks(range(len(client_order)))
  ax.set_xticklabels([str(c) for c in client_order])

  ax.set_title(f"Interval: {interval} ms", fontweight="bold", pad=8)

  ax.set_xlabel("Number of Clients")
  ax.set_ylabel("RTT (ms, log scale)")

  ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5)

  ax.set_axisbelow(True)
  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)

  # Remove individual subplot legends.
  if ax.get_legend():
    ax.get_legend().remove()

# Hide unused panels if there are fewer than four intervals.
for j in range(len(intervals), len(axes)):
  axes[j].set_visible(False)

# ============================================================
# Shared legend at the top
# ============================================================

# Library color swatches.
library_handles = [
    Patch(facecolor=palette[lib], edgecolor="gray", label=library_labels.get(lib, lib))
    for lib in library_order
]

# P99 diamond marker.
p99_handle = Line2D(
    [0],
    [0],
    marker="D",
    linestyle="none",
    markerfacecolor="white",
    markeredgecolor="black",
    markersize=5,
    label="P99 RTT",
)

# Confidence interval error-bar symbol.
ci_handle = Line2D(
    [0],
    [0],
    color="black",
    marker="|",
    markersize=10,
    linewidth=1,
    label="95% confidence interval of P99 RTT",
)

all_handles = library_handles + [p99_handle, ci_handle]

fig.legend(
    handles=all_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.015),
    ncol=5,
    frameon=False,
    fontsize=8,
    title="WebSocket Libraries and RTT Metrics",
    title_fontsize=10,
)

# Leave enough room for the legend.
plt.tight_layout(rect=[0, 0, 1, 0.91])

plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")

plt.show()

print(f"Graph saved to: {OUTPUT_FILE}")