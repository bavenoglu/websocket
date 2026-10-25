import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

# ============================================================
# Configuration
# ============================================================
INPUT_FILE = "final_performance_report_averages.csv"
OUTPUT_FILE = "throughput.png"

# ============================================================
# Load data
# ============================================================
df = pd.read_csv(INPUT_FILE)

required_columns = [
    "Library",
    "ClientCount",
    "MsgSize",
    "Interval",
    "Timeout",
    "Throughput_Msg_s",
]

missing = set(required_columns) - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {sorted(missing)}")

df["Throughput_Msg_s"] = pd.to_numeric(
    df["Throughput_Msg_s"], errors="coerce"
)
df = df.dropna(
    subset=[
        "Library",
        "ClientCount",
        "MsgSize",
        "Interval",
        "Throughput_Msg_s",
    ]
)

# Average throughput across timeout settings.
# Each configuration has four timeout values in this dataset.
plot_df = (
    df.groupby(
        ["Library", "ClientCount", "MsgSize", "Interval"],
        as_index=False,
    )["Throughput_Msg_s"]
    .mean()
)

# ============================================================
# Ordering and display labels
# ============================================================
client_counts = sorted(plot_df["ClientCount"].unique())
message_sizes = sorted(plot_df["MsgSize"].unique())

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
    "node.js-uws": "Node.js-µWebSockets",
    "PHP-Swoole": "PHP-Swoole",
    "go": "Go-gorilla",
    "Python-websockets": "Python-websockets",
}

# Keep a consistent color for each library in every subplot.
colors = {
    "Java-WebSocket": "#3498db",
    "Java-Netty": "#ff7f0e",
    "Node-ws": "#2ca02c",
    "node.js-uws": "#e53935",
    "PHP-Swoole": "#9467bd",
    "go": "#8c564b",
    "Python-websockets": "#e377c2",
}

markers = {
    "Java-WebSocket": "o",
    "Java-Netty": "o",
    "Node-ws": "o",
    "node.js-uws": "o",
    "PHP-Swoole": "o",
    "go": "o",
    "Python-websockets": "o",
}

# ============================================================
# Publication-style plot configuration
# ============================================================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.2,
    "lines.markersize": 3,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# One row per client count, one column per message size.
fig, axes = plt.subplots(
    nrows=len(client_counts),
    ncols=len(message_sizes),
    figsize=(12, 2.05 * len(client_counts)),
    sharex=True,
    sharey="row",
    squeeze=False,
)

# ============================================================
# Draw subplots
# ============================================================
for row, client_count in enumerate(client_counts):

    for col, msg_size in enumerate(message_sizes):
        ax = axes[row, col]

        subset = plot_df[
            (plot_df["ClientCount"] == client_count)
            & (plot_df["MsgSize"] == msg_size)
        ]

        for library in library_order:
            lib_data = subset[
                subset["Library"] == library
            ].sort_values("Interval")

            if lib_data.empty:
                continue

            ax.plot(
                lib_data["Interval"],
                lib_data["Throughput_Msg_s"],
                label=library_labels.get(library, library),
                color=colors.get(library, "gray"),
                marker=markers.get(library, "o"),
                linewidth=1.2,
                markersize=3,
                alpha=0.95,
            )

        # Column headings
        if row == 0:
            if msg_size == 100:
                size_label = "100 B"
            elif msg_size == 33000:
                size_label = "33K"
            elif msg_size == 66000:
                size_label = "66K"
            else:
                size_label = f"{msg_size:,} B"

            ax.set_title(f"Msg Size: {size_label}", pad=5)

        # Axis labels, matching the reference layout
        if col == 0:
            ax.set_ylabel("Mean Throughput")
            ax.yaxis.set_major_formatter(
                StrMethodFormatter("{x:,.0f}")
            )

        if row == len(client_counts) - 1:
            ax.set_xlabel("Msg Interval (ms)")

        # Client count on the right side of each row
        if col == len(message_sizes) - 1:
            ax.text(
                1.025,
                0.5,
                f"No. of Clients: {client_count}",
                transform=ax.transAxes,
                rotation=-90,
                va="center",
                ha="left",
                fontsize=7,
            )

        # Grid and axes styling
        ax.grid(
            True,
            which="major",
            linestyle="--",
            linewidth=0.5,
            alpha=0.45,
        )

        ax.set_xticks(sorted(plot_df["Interval"].unique()))
        ax.tick_params(
            axis="both",
            direction="out",
            length=2.5,
            width=0.6,
        )

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

# ============================================================
# Shared legend across the top
# ============================================================
handles, labels = axes[0, 0].get_legend_handles_labels()

# Retain only libraries actually present in the data.
present_libraries = set(plot_df["Library"].unique())
legend_items = [
    (h, library_labels.get(lib, lib))
    for h, lib in zip(handles, labels)
]

# Build legend from the first subplot's actual handles.
fig.legend(
    handles,
    labels,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.005),
    ncol=7,
    frameon=False,
    title="WebSocket Library",
    title_fontsize=9,
    handlelength=1.8,
    columnspacing=1.2,
)

fig.tight_layout(
    rect=[0.025, 0.015, 0.98, 0.975],
    h_pad=1.5,
    w_pad=1.0,
)

# Save and display
fig.savefig(
    OUTPUT_FILE,
    dpi=300,
    bbox_inches="tight",
    facecolor="white",
)

plt.show()

print(f"Figure saved to: {OUTPUT_FILE}")
