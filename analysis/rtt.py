import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ==============================
# CONFIGURATION
# ==============================

INPUT_FILE = Path("final_performance_report_averages.csv")
OUTPUT_FILE = Path("rtt.png")
DPI = 300

PARAMS = {
    "ClientCount": {
        "short": "N",
        "label": "No. of Clients",
        "fmt": lambda x: f"N={x:,}",
    },
    "Interval": {
        "short": "I",
        "label": "Msg Interval (ms)",
        "fmt": lambda x: f"I={x}",
    },
    "Timeout": {
        "short": "T",
        "label": "Timeout (ms)",
        "fmt": lambda x: f"T={x:,}",
    },
    "MsgSize": {
        "short": "S",
        "label": "Msg Size",
        "fmt": lambda x: f"S={x:,}B",
    },
}

# Desired order; any libraries not listed here are appended automatically.
PREFERRED_LIBRARY_ORDER = [
    "Java-WebSocket",
    "Java-Netty",
    "Node-ws",
    "node.js-uws",
    "PHP-Swoole",
    "go",
    "Python-websockets",
]

# Display names in the figure
DISPLAY_NAMES = {
    "Java-WebSocket": "Java-WebSocket",
    "Java-Netty": "Java-Netty",
    "Node-ws": "Node.js-ws",
    "node.js-uws": "Node.js-µWebSockets",
    "PHP-Swoole": "PHP-Swoole",
    "go": "Go-gorilla",
    "Python-websockets": "Python-websockets",
}

# ==============================
# LOAD AND VALIDATE DATA
# ==============================

df = pd.read_csv(INPUT_FILE)

required_columns = [
    "Library",
    "ClientCount",
    "Interval",
    "Timeout",
    "MsgSize",
    "Avg_RTT_ms",
]

missing = set(required_columns) - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {sorted(missing)}")

df = df[required_columns].copy()
df["Avg_RTT_ms"] = pd.to_numeric(df["Avg_RTT_ms"], errors="coerce")
df = df.dropna(subset=required_columns)

observed_libraries = df["Library"].unique().tolist()
libraries = [
    lib for lib in PREFERRED_LIBRARY_ORDER if lib in observed_libraries
]
libraries += [
    lib for lib in observed_libraries if lib not in libraries
]

if len(libraries) < 2:
    raise ValueError("At least two libraries are needed to calculate rankings.")

# ==============================
# CALCULATE RANKS
# ==============================
# For each complete experimental configuration, rank libraries by Avg_RTT_ms.
# Lowest RTT gets rank 1. Tied values receive average ranks.
#
# Then, for each heatmap, average each library's ranks over the two parameters
# not shown in that heatmap. Thus, cells are MEAN RANKS, not RTT measurements.

all_params = [
    "ClientCount",
    "Interval",
    "Timeout",
    "MsgSize",
]

ranked = df.copy()
ranked["Rank"] = ranked.groupby(all_params)["Avg_RTT_ms"].rank(
    method="average",
    ascending=True,
)

# Each tuple defines the two parameters displayed in a heatmap.
panels = [
    ("ClientCount", "Interval"),
    ("ClientCount", "Timeout"),
    ("ClientCount", "MsgSize"),
    ("Interval", "Timeout"),
    ("Interval", "MsgSize"),
    ("Timeout", "MsgSize"),
]


def format_row_label(row, row_params):
    return ", ".join(
        PARAMS[param]["fmt"](row[param]) for param in row_params
    )


def make_heatmap_data(data, row_params, library_order):
    # Average ranks across all remaining parameters.
    summary = (
        data.groupby(row_params + ["Library"], as_index=False)["Rank"]
        .mean()
    )

    # Build a row label from the two displayed parameter values.
    summary["Condition"] = summary.apply(
        lambda row: format_row_label(row, row_params), axis=1
    )

    # Preserve ascending numeric parameter order.
    conditions = (
        summary[row_params + ["Condition"]]
        .drop_duplicates()
        .sort_values(row_params)["Condition"]
        .tolist()
    )

    matrix = summary.pivot(
        index="Condition", columns="Library", values="Rank"
    )
    matrix = matrix.reindex(index=conditions, columns=library_order)

    return matrix


# ==============================
# PLOT SIX HEATMAPS
# ==============================

sns.set_theme(style="white", font_scale=0.78)

fig, axes = plt.subplots(3, 2, figsize=(19, 23))
axes = axes.flatten()

for ax, row_params in zip(axes, panels):
    matrix = make_heatmap_data(ranked, list(row_params), libraries)

    row_title = " vs ".join(PARAMS[p]["label"] for p in row_params)
    ax.set_title(
        f"Rankings: {row_title}",
        fontsize=12,
        fontweight="bold",
        pad=9,
    )

    sns.heatmap(
        matrix,
        ax=ax,
        annot=True,
        fmt=".1f",
        cmap="RdYlGn_r",
        vmin=1,
        vmax=len(libraries),
        linewidths=0.35,
        linecolor="white",
        cbar=True,
        cbar_kws={
            "label": "Mean Rank (1 = Best)",
            "shrink": 0.92,
        },
        annot_kws={"fontsize": 7.5},
    )

    ax.set_xlabel("WebSocket Library", fontsize=9)
    ax.set_ylabel("Experimental setting", fontsize=9)

    display_labels = [
        DISPLAY_NAMES.get(lib, lib) for lib in matrix.columns
    ]
    ax.set_xticklabels(
        display_labels,
        rotation=45,
        ha="right",
        rotation_mode="anchor",
        fontsize=8,
    )
    ax.set_yticklabels(
        ax.get_yticklabels(),
        rotation=0,
        fontsize=7.5,
    )

plt.tight_layout()
fig.savefig(OUTPUT_FILE, dpi=DPI, bbox_inches="tight")
plt.show()

print(f"Figure saved to: {OUTPUT_FILE.resolve()}")
