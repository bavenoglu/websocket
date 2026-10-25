import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# Configuration
# ============================================================
INPUT_FILE = "final_performance_report_averages.csv"
OUTPUT_FILE = "msgserver.png"

VALUE_COLUMN = "Msg_Success_%"

# Display names and order in the legend
library_order = [
    "Java-WebSocket",
    "Java-Netty",
    "Node-ws",
    "node.js-uws",
    "PHP-Swoole",
    "go",
    "Python-websockets"
]

library_labels = {
    "Java-WebSocket": "Java-WebSocket",
    "Java-Netty": "Java-Netty",
    "Node-ws": "Node.js-ws",
    "node.js-uws": "Node.js-µWebSockets",
    "PHP-Swoole": "PHP-Swoole",
    "go": "Go-gorilla",
    "Python-websockets": "Python-websockets"
}

# Colors corresponding to the reference figure
colors = {
    "Java-WebSocket": "#287FB5",
    "Java-Netty": "#FF800D",
    "Node-ws": "#D9272E",
    "node.js-uws": "#945B50",
    "PHP-Swoole": "#D96BB5",
    "go": "#B5BE20",
    "Python-websockets": "#19B8C7"
}

# ============================================================
# Read data
# ============================================================
df = pd.read_csv(INPUT_FILE)

required_columns = [
    "Library", "ClientCount", "Interval",
    "Timeout", "MsgSize", VALUE_COLUMN
]

missing = set(required_columns) - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {sorted(missing)}")

df[VALUE_COLUMN] = pd.to_numeric(
    df[VALUE_COLUMN], errors="coerce"
)

df = df.dropna(subset=["Library", VALUE_COLUMN])

# ============================================================
# Define the four groups shown in the reference figure
# ============================================================
groups = [
    {
        "column": "ClientCount",
        "title": "No. of Clients",
        "labels": lambda values: [
            f"{int(v):,}" for v in values
        ]
    },
    {
        "column": "Interval",
        "title": "Msg Interval (ms)",
        "labels": lambda values: [
            f"{int(v):,}" for v in values
        ]
    },
    {
        "column": "Timeout",
        "title": "Timeout (ms)",
        "labels": lambda values: [
            f"{int(v):,}" for v in values
        ]
    },
    {
        "column": "MsgSize",
        "title": "Msg Size",
        "labels": lambda values: [
            f"{int(v) // 1000}K" if v >= 1000
            else f"{int(v)}B"
            for v in values
        ]
    }
]

# Sort category values numerically
for group in groups:
    column = group["column"]
    group["values"] = sorted(df[column].dropna().unique())

    # Average Msg_Success_% across all other experimental
    # parameters for each library and category value.
    grouped = (
        df.groupby(["Library", column], as_index=False)
          [VALUE_COLUMN]
          .mean()
    )

    # Rows: libraries; columns: category values
    pivot = grouped.pivot(
        index="Library",
        columns=column,
        values=VALUE_COLUMN
    )

    group["data"] = pivot.reindex(
        index=library_order,
        columns=group["values"]
    )

    group["tick_labels"] = group["labels"](
        group["values"]
    )

# ============================================================
# Plot
# ============================================================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "axes.titlesize": 12,
    "figure.dpi": 150,
    "savefig.dpi": 300
})

fig, ax = plt.subplots(figsize=(18, 4.8))

bar_width = 0.12
group_gap = 1.1

x_positions = []
tick_positions = []
group_centers = []
group_boundaries = []

current_x = 0.0

for group_index, group in enumerate(groups):
    values = group["values"]
    data = group["data"]
    n_categories = len(values)

    # Position of each category in this group
    positions = (
        current_x
        + np.arange(n_categories) * 1.0
    )

    x_positions.append(positions)
    tick_positions.extend(positions)

    # Plot one bar per library for every category
    for library_index, library in enumerate(library_order):
        offsets = (
            positions
            + (library_index - (len(library_order) - 1) / 2)
            * bar_width
        )

        heights = data.loc[library].to_numpy(dtype=float)

        ax.bar(
            offsets,
            heights,
            width=bar_width,
            color=colors[library],
            edgecolor="black",
            linewidth=0.35,
            label=library_labels[library]
            if group_index == 0 else None
        )

    group_centers.append(
        (positions[0] + positions[-1]) / 2
    )

    group_boundaries.append(
        (positions[0] + positions[-1]) / 2
    )

    # Add space before the next group
    current_x = positions[-1] + 1.0 + group_gap

# ============================================================
# Category tick labels
# ============================================================
all_tick_labels = []

for group in groups:
    all_tick_labels.extend(group["tick_labels"])

ax.set_xticks(tick_positions)
ax.set_xticklabels(all_tick_labels, rotation=25, ha="right")

# ============================================================
# Group titles beneath the x-axis
# ============================================================
for center, group in zip(group_centers, groups):
    ax.text(
        center, -0.145,
        group["title"],
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=11,
        fontweight="bold"
    )

# ============================================================
# Formatting
# ============================================================
ax.set_ylabel("Successful Message Delivery (%)")
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 10))
ax.set_yticklabels([f"{v}%" for v in range(0, 101, 10)])

ax.grid(
    axis="y",
    linestyle="--",
    linewidth=0.5,
    alpha=0.35
)
ax.set_axisbelow(True)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.legend(
    title="WebSocket Library",
    ncol=7,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.22),
    frameon=False,
    columnspacing=1.5,
    handlelength=1.8
)

ax.margins(x=0.02)

plt.subplots_adjust(
    left=0.055,
    right=0.99,
    bottom=0.27,
    top=0.78
)

plt.savefig(
    OUTPUT_FILE,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print(f"Chart saved to: {OUTPUT_FILE}")