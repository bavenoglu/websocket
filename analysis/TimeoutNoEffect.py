import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ============================================================
# Configuration
# ============================================================
INPUT_FILE = "final_performance_report_averages.csv"
OUTPUT_FILE = "timeoutnoeffect.png"

# Assuming the throughput column is named "Throughput" 
# (change this if your CSV uses a different column name)
VALUE_COLUMN = "Throughput_Msg_s"

library_order = [
    "go",
    "Java-Netty",
    "Java-WebSocket",
    "Node-ws",
    "node.js-uws",
    "PHP-Swoole",
    "Python-websockets"
]

library_labels = {
    "go": "Go-gorilla",
    "Java-Netty": "Java-Netty",
    "Java-WebSocket": "Java-WebSocket",
    "Node-ws": "Node.js-ws",
    "node.js-uws": "Node.js-µWebSockets",
    "PHP-Swoole": "PHP-Swoole",
    "Python-websockets": "Python-websockets"
}

# ============================================================
# Read and Validate Data
# ============================================================
df = pd.read_csv(INPUT_FILE)

required_columns = ["Library", "Timeout", "MsgSize", VALUE_COLUMN]
missing = set(required_columns) - set(df.columns)
if missing:
    raise ValueError(f"Missing columns in CSV: {sorted(missing)}")

df[VALUE_COLUMN] = pd.to_numeric(df[VALUE_COLUMN], errors="coerce")
df = df.dropna(subset=required_columns)

# ============================================================
# Plot Setup
# ============================================================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.titlesize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 300
})

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# ------------------------------------------------------------
# Subplot 1: WebSocket Library vs. Timeout
# ------------------------------------------------------------
# Aggregate mean throughput grouped by Library and Timeout
df_lib_timeout = (
    df.groupby(["Library", "Timeout"], as_index=False)[VALUE_COLUMN]
    .mean()
)

pivot_lib_timeout = df_lib_timeout.pivot(
    index="Library",
    columns="Timeout",
    values=VALUE_COLUMN
).reindex(index=library_order)

# Rename index for display labels
pivot_lib_timeout.index = [library_labels[lib] for lib in pivot_lib_timeout.index]

sns.heatmap(
    pivot_lib_timeout,
    ax=axes[0],
    cmap="YlGnBu",
    annot=True,
    fmt=",.0f",
    cbar=True,
    linewidths=0.5,
    linecolor="white",
    cbar_kws={"shrink": 0.8}
)

axes[0].set_title(
    "Throughput: WebSocket Library vs Timeout\n(Uniform rows = No Effect)",
    fontweight="bold",
    pad=10
)
axes[0].set_xlabel("Timeout (ms)")
axes[0].set_ylabel("WebSocket Library")
axes[0].set_yticklabels(axes[0].get_yticklabels(), rotation=0)

# ------------------------------------------------------------
# Subplot 2: Msg Size vs. Timeout
# ------------------------------------------------------------
# Aggregate mean throughput grouped by MsgSize and Timeout
df_size_timeout = (
    df.groupby(["MsgSize", "Timeout"], as_index=False)[VALUE_COLUMN]
    .mean()
)

pivot_size_timeout = df_size_timeout.pivot(
    index="MsgSize",
    columns="Timeout",
    values=VALUE_COLUMN
)

sns.heatmap(
    pivot_size_timeout,
    ax=axes[1],
    cmap="YlGnBu",
    annot=True,
    fmt=",.0f",
    cbar=True,
    linewidths=0.5,
    linecolor="white",
    cbar_kws={"shrink": 0.8}
)

axes[1].set_title(
    "Throughput: Msg Size vs Timeout (ms)\n(Uniform rows = No Effect)",
    fontweight="bold",
    pad=10
)
axes[1].set_xlabel("Timeout (ms)")
axes[1].set_ylabel("Msg Size")
axes[1].set_yticklabels(axes[1].get_yticklabels(), rotation=0)

# ============================================================
# Final Layout Adjustments & Save
# ============================================================
plt.tight_layout()
plt.savefig(OUTPUT_FILE, bbox_inches="tight")
plt.show()

print(f"Heatmap chart saved to: {OUTPUT_FILE}")