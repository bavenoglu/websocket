#!/usr/bin/env python3
"""
Generate six WebSocket benchmark heatmaps from
final_performance_report_averages.csv.

Each original cell is divided into two half-cells:
    Left:  mean Avg_RTT_ms (milliseconds)
    Right: mean Msg_Succ_Actual (success percentage)

Normalization:
    RTT: row-based
        Green = lowest/best RTT
        Red   = highest/worst RTT

    Success percentage: row-based
        Light blue = lowest success
        Dark blue  = highest success
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Rectangle


CSV_PATH = Path("final_performance_report_averages.csv")
OUTPUT_PATH = Path("websocket_rtt_with_msg_success.png")


# Library order and display names.
LIBRARY_ORDER = [
    "Java-WebSocket",
    "Java-Netty",
    "Node-ws",
    "node.js-uws",
    "PHP-Swoole",
    "go",
    "Python-websockets",
]

LIBRARY_LABELS = [
    "Java-WebSocket",
    "Java-Netty",
    "Node.js-ws",
    "Node.js-µWebSockets",
    "PHP-Swoole",
    "Go-gorilla",
    "Python-websockets",
]


CLIENT_ORDER = [1, 32, 128, 512, 2048]
INTERVAL_ORDER = [1, 2, 5, 10]
TIMEOUT_ORDER = [500, 2000, 5000, 10000]
SIZE_ORDER = [100, 33000, 66000]


# Six experimental views.
PANELS = [
    {
        "title": "No. of Clients vs Msg Interval (ms)",
        "row_keys": ["ClientCount", "Interval"],
        "row_order": [
            (n, i)
            for n in CLIENT_ORDER
            for i in INTERVAL_ORDER
        ],
        "row_label": lambda r: f"N={r[0]}, I={r[1]}",
        "group_by": ["ClientCount", "Interval"],
    },
    {
        "title": "No. of Clients vs Timeout (ms)",
        "row_keys": ["ClientCount", "Timeout"],
        "row_order": [
            (n, t)
            for n in CLIENT_ORDER
            for t in TIMEOUT_ORDER
        ],
        "row_label": lambda r: f"N={r[0]}, T={r[1]:,}",
        "group_by": ["ClientCount", "Timeout"],
    },
    {
        "title": "No. of Clients vs Msg Size (bytes)",
        "row_keys": ["ClientCount", "MsgSize"],
        "row_order": [
            (n, s)
            for n in CLIENT_ORDER
            for s in SIZE_ORDER
        ],
        "row_label": lambda r: f"N={r[0]}, S={r[1]:,}",
        "group_by": ["ClientCount", "MsgSize"],
    },
    {
        "title": "Msg Interval (ms) vs Timeout (ms)",
        "row_keys": ["Interval", "Timeout"],
        "row_order": [
            (i, t)
            for i in INTERVAL_ORDER
            for t in TIMEOUT_ORDER
        ],
        "row_label": lambda r: f"I={r[0]}, T={r[1]:,}",
        "group_by": ["Interval", "Timeout"],
    },
    {
        "title": "Msg Interval (ms) vs Msg Size (bytes)",
        "row_keys": ["Interval", "MsgSize"],
        "row_order": [
            (i, s)
            for i in INTERVAL_ORDER
            for s in SIZE_ORDER
        ],
        "row_label": lambda r: f"I={r[0]}, S={r[1]:,}",
        "group_by": ["Interval", "MsgSize"],
    },
    {
        "title": "Timeout (ms) vs Msg Size (bytes)",
        "row_keys": ["Timeout", "MsgSize"],
        "row_order": [
            (t, s)
            for t in TIMEOUT_ORDER
            for s in SIZE_ORDER
        ],
        "row_label": lambda r: f"T={r[0]:,}, S={r[1]:,}",
        "group_by": ["Timeout", "MsgSize"],
    },
]


def normalize_by_row(values, reverse=False):
    """
    Normalize values independently within each row.

    reverse=False:
        Minimum = 0, maximum = 1.

    reverse=True:
        Maximum = 0, minimum = 1.

    Missing values remain NaN.
    Rows with identical finite values are assigned 0.5.
    """
    normalized = np.full_like(values, np.nan, dtype=float)

    for r in range(values.shape[0]):
        row = values[r, :]
        finite = np.isfinite(row)

        if not finite.any():
            continue

        lo = np.min(row[finite])
        hi = np.max(row[finite])

        if np.isclose(lo, hi):
            normalized[r, finite] = 0.5

        elif reverse:
            normalized[r, finite] = (
                (hi - row[finite]) / (hi - lo)
            )

        else:
            normalized[r, finite] = (
                (row[finite] - lo) / (hi - lo)
            )

    return normalized


def readable_text_color(normalized_value, metric):
    """Choose readable text contrast for each metric's background."""
    if not np.isfinite(normalized_value):
        return "#333333"

    if metric == "success":
        # Blues: yüksek normalize değer koyu mavi -> beyaz yazı, düşük değer açık mavi -> siyah yazı.
        return (
            "white"
            if normalized_value > 0.55
            else "black"
        )

    # RTT (Reds): 0 = açık renk (en iyi), 1 = koyu renk (en kötü).
    # Sadece koyu arka planlarda (> 0.65) beyaz yazı, açık arka planlarda siyah yazı kullanıyoruz.
    return (
        "white"
        if normalized_value > 0.65
        else "black"
    )


def draw_split_heatmap(
    ax,
    rtt_values,
    success_values,
    rtt_normalized,
    success_normalized,
    rtt_cmap,
    success_cmap,
):
    """
    Draw each logical cell as two half-width cells.

    Left half: RTT, green-yellow-red.
    Right half: success percentage, light-to-dark blue.
    """
    nrows, ncols = rtt_values.shape

    # Leave a narrow white gap between library groups.
    # The two metric half-cells remain adjacent within each library.
    library_gap = 0.08
    half_width = (1.0 - library_gap) / 2.0

    for r in range(nrows):
        for c in range(ncols):
            rtt = rtt_values[r, c]
            success = success_values[r, c]

            x_left = c + library_gap / 2.0
            x_right = x_left + half_width

            # --------------------------------
            # Left half: RTT in milliseconds
            # --------------------------------
            rtt_norm = rtt_normalized[r, c]

            if np.isfinite(rtt):
                rtt_color = rtt_cmap(rtt_norm)
                rtt_text = f"{rtt:.2f}"
            else:
                rtt_color = "#eeeeee"
                rtt_text = "N/A"

            ax.add_patch(
                Rectangle(
                    (x_left, r),
                    half_width,
                    1.0,
                    facecolor=rtt_color,
                    edgecolor="black",
                    linewidth=0.55,
                )
            )

            ax.text(
                x_left + half_width / 2.0,
                r + 0.5,
                rtt_text,
                ha="center",
                va="center",
                fontsize=5.5,
                color=readable_text_color(rtt_norm, "rtt"),
            )

            # --------------------------------
            # Right half: Success percentage
            # --------------------------------
            success_norm = success_normalized[r, c]

            if np.isfinite(success):
                success_color = success_cmap(success_norm)
                success_text = f"{success:.1f}%"
            else:
                success_color = "#eeeeee"
                success_text = "N/A"

            ax.add_patch(
                Rectangle(
                    (x_right, r),
                    half_width,
                    1.0,
                    facecolor=success_color,
                    edgecolor="black",
                    linewidth=0.55,
                )
            )

            ax.text(
                x_right + half_width / 2.0,
                r + 0.5,
                success_text,
                ha="center",
                va="center",
                fontsize=5.5,
                color=readable_text_color(
                    success_norm,
                    "success",
                ),
            )

    ax.set_xlim(0, ncols)
    ax.set_ylim(nrows, 0)


def main():
    # Read the input CSV.
    df = pd.read_csv(CSV_PATH)

    required = {
        "Library",
        "ClientCount",
        "Interval",
        "Timeout",
        "MsgSize",
        "Avg_RTT_ms",
        "Msg_Succ_Actual",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}"
        )

    # Convert numerical columns to numeric types.
    numeric_columns = [
        "ClientCount",
        "Interval",
        "Timeout",
        "MsgSize",
        "Avg_RTT_ms",
        "Msg_Succ_Actual",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove records that cannot contribute to the metrics.
    df = df.dropna(
        subset=[
            "Library",
            "ClientCount",
            "Interval",
            "Timeout",
            "MsgSize",
            "Avg_RTT_ms",
            "Msg_Succ_Actual",
        ]
    )

    # Validate libraries and preserve their requested order.
    available = [
        lib
        for lib in LIBRARY_ORDER
        if lib in set(df["Library"])
    ]

    if len(available) != len(LIBRARY_ORDER):
        absent = sorted(set(LIBRARY_ORDER) - set(available))
        raise ValueError(
            f"Expected libraries not found in CSV: {absent}"
        )

    display_labels = dict(zip(LIBRARY_ORDER, LIBRARY_LABELS))

    # RTT: green = best, red = worst.
    rtt_cmap = plt.get_cmap("Reds")

    # Success percentage: light blue = low, dark blue = high.
    success_cmap = plt.get_cmap("Blues")

    # Create six panels in a 3 x 2 layout.
    fig, axes = plt.subplots(
        3,
        2,
        figsize=(16, 21),
        constrained_layout=False,
    )

    axes = axes.flatten()

    for ax, panel in zip(axes, PANELS):
        group_by = panel["group_by"]

        # Average metrics across dimensions not shown in this panel.
        summary = (
            df.groupby(group_by + ["Library"], as_index=False)
            .agg(
                Avg_RTT_ms=("Avg_RTT_ms", "mean"),
                Msg_Succ_Actual=("Msg_Succ_Actual", "mean"),
            )
        )

        # Rows = experimental settings, columns = libraries.
        rtt_pivot = summary.pivot(
            index=group_by,
            columns="Library",
            values="Avg_RTT_ms",
        )

        success_pivot = summary.pivot(
            index=group_by,
            columns="Library",
            values="Msg_Succ_Actual",
        )

        # Reindex both metrics to the requested row and library order.
        index = pd.MultiIndex.from_tuples(
            panel["row_order"],
            names=group_by,
        )

        rtt_pivot = rtt_pivot.reindex(
            index=index,
            columns=available,
        )

        success_pivot = success_pivot.reindex(
            index=index,
            columns=available,
        )

        rtt_values = rtt_pivot.to_numpy(dtype=float)
        success_values = success_pivot.to_numpy(dtype=float)

        # RTT: row-based normalization.
        # Compare libraries under the same experimental setting.
        rtt_normalized = normalize_by_row(
            rtt_values,
            reverse=False,
        )

        # Success: row-based normalization.
        # Compare libraries under the same experimental setting.
        # With the Blues colormap, higher normalized values are darker blue.
        success_normalized = normalize_by_row(
            success_values,
            reverse=True,
        )

        # Draw split cells.
        draw_split_heatmap(
            ax=ax,
            rtt_values=rtt_values,
            success_values=success_values,
            rtt_normalized=rtt_normalized,
            success_normalized=success_normalized,
            rtt_cmap=rtt_cmap,
            success_cmap=success_cmap,
        )

        nrows, ncols = rtt_values.shape

        # Library labels centered over the original cell width.
        ax.set_xticks(np.arange(ncols) + 0.5)

        ax.set_xticklabels(
            [display_labels[lib] for lib in available],
            rotation=28,
            ha="right",
            rotation_mode="anchor",
            fontsize=7.2,
        )

        # Experimental setting labels.
        ax.set_yticks(np.arange(nrows) + 0.5)

        ax.set_yticklabels(
            [
                panel["row_label"](tuple(row))
                for row in panel["row_order"]
            ],
            fontsize=7.0,
        )

        ax.set_title(
            panel["title"],
            fontsize=10,
            fontweight="bold",
            pad=8,
        )

        ax.set_xlabel(
            "WebSocket Library",
            fontsize=8,
            labelpad=7,
        )

        ax.set_ylabel(
            "Experimental Setting",
            fontsize=8,
            labelpad=5,
        )

        ax.tick_params(axis="both", length=0)

        # Hide external axes borders.
        for spine in ax.spines.values():
            spine.set_visible(False)

    # --------------------------------
    # RTT colorbar
    # --------------------------------
    rtt_sm = ScalarMappable(
        norm=Normalize(0, 1),
        cmap=rtt_cmap,
    )
    rtt_sm.set_array([])

    rtt_cbar_ax = fig.add_axes([0.12, 0.04, 0.32, 0.014])

    rtt_cbar = fig.colorbar(
        rtt_sm,
        cax=rtt_cbar_ax,
        orientation="horizontal",
    )

    rtt_cbar.set_ticks([0, 0.5, 1])
    rtt_cbar.set_ticklabels(
        ["Best RTT", "Median", "Worst RTT"]
    )
    rtt_cbar.ax.tick_params(labelsize=7, length=0)

    fig.text(
        0.28,
        0.06,
        "RTT (ms): Dark Red = Worst, Light Red = Best (per row)",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
    )

    # --------------------------------
    # Success percentage colorbar
    # --------------------------------
    success_sm = ScalarMappable(
        norm=Normalize(0, 1),
        cmap=success_cmap,
    )
    success_sm.set_array([])

    success_cbar_ax = fig.add_axes(
        [0.56, 0.04, 0.32, 0.014]
    )

    success_cbar = fig.colorbar(
        success_sm,
        cax=success_cbar_ax,
        orientation="horizontal",
    )

    # Row-based normalization with the Blues colormap:
    # normalized 0 = lowest success (light blue),
    # normalized 1 = highest success (dark blue).
    success_cbar.set_ticks([0, 0.5, 1])
    success_cbar.set_ticklabels(
        ["Lowest Success", "Median", "Highest Success"]
    )
    success_cbar.ax.tick_params(labelsize=7, length=0)

    fig.text(
        0.72,
        0.06,
        "Success (%): Dark Blue = Worst, Light Blue = Best (per row)",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
    )

    # Explain the split-cell format.
    fig.text(
        0.5,
        0.018,
        "Each library cell: left = RTT (ms), right = success (%)",
        ha="center",
        va="center",
        fontsize=8,
    )

    # Adjust figure spacing.
    fig.subplots_adjust(
        left=0.10,
        right=0.985,
        top=0.975,
        bottom=0.105,
        hspace=0.25,
        wspace=0.25,
    )

    # Save the figure.
    fig.savefig(
        OUTPUT_PATH,
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(fig)

    print(f"Saved heatmaps to: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()