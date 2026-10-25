#!/usr/bin/env python3
"""
Create one figure with six subplots for all requested parameter pairs.

Each subplot:
  * x-axis = the first parameter in the pair
  * each line-series is a Library + value of the second parameter
  * Average_RTT_ms, Median_RTT_ms, P50_RTT_ms, P95_RTT_ms, P99_RTT_ms
    are shown as markers (different marker shape per metric)
  * P50_Upper_ms, P95_Lower_ms, P95_Upper_ms, P99_Lower_ms, P99_Upper_ms
    are shown as lines (different line style per bound)
  * the two parameters not named in the subplot are averaged over

Colors identify libraries consistently. Marker shape identifies the RTT metric.
The legend explains line styles (confidence-bound columns) separately.

Example:
  python plot_rtt_parameter_pairs.py --csv "final_performance_report_averages(2).csv"
  python plot_rtt_parameter_pairs.py --csv data.csv --log-y
"""

import argparse
from pathlib import Path
import math
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

PARAM_PAIRS = [
    ("ClientCount", "Interval"),
    ("ClientCount", "Timeout"),
    ("ClientCount", "MsgSize"),
    ("Interval", "Timeout"),
    ("Interval", "MsgSize"),
    ("Timeout", "MsgSize"),
]


METRICS = {
    "Average RTT": ("Avg_RTT_ms", "o"),
    "Median RTT": ("Median_RTT_ms", "s"),
    "P99 RTT": ("P99_RTT_ms", "D"),
}

BOUNDS = {
    "P99 lower": ("P99_Lower_ms", ":"),
    "P99 upper": ("P99_Upper_ms", "-."),
}



REQUIRED = [
    "Library", "ClientCount", "Interval", "Timeout", "MsgSize",
    "Avg_RTT_ms", "Median_RTT_ms", "P99_RTT_ms",
    "P99_Lower_ms", "P99_Upper_ms",
]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", default=None,
                   help="Input CSV path (default: CSV beside this script)")
    p.add_argument("--output-prefix", default=None,
                   help="Output filename prefix (default: beside this script)")
    p.add_argument("--log-y", action="store_true", help="Use logarithmic Y axis")
    p.add_argument("--linear-y", action="store_true", help="Force linear Y axis (default)")
    p.add_argument("--fig-width", type=float, default=22)
    p.add_argument("--fig-height", type=float, default=25)
    return p.parse_args()


def main():
    args = parse_args()
    script_dir = Path(__file__).resolve().parent

    csv_path = (
        Path(args.csv)
        if args.csv
        else script_dir / "final_performance_report_averages.csv"
    )
    if not csv_path.is_absolute():
        csv_path = Path.cwd() / csv_path

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV not found: {csv_path.resolve()}\n"
            "Use --csv to provide the path to the input CSV."
        )

    df = pd.read_csv(csv_path)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(
            "CSV is missing required columns: " + ", ".join(missing)
        )

    params = ["ClientCount", "Interval", "Timeout", "MsgSize"]
    value_cols = (
        [v[0] for v in METRICS.values()]
        + [v[0] for v in BOUNDS.values()]
    )

    for col in params + value_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Library"] + params)

    libraries = sorted(df["Library"].dropna().unique())
    cmap = plt.get_cmap("tab10")
    colors = {
        lib: cmap(i % 10)
        for i, lib in enumerate(libraries)
    }

    # Each subplot uses one parameter on X.
    # Average across the other three parameters.
    fig, axes = plt.subplots(
        2, 2,
        figsize=(args.fig_width, args.fig_height * 0.65),
        constrained_layout=False
    )
    axes = axes.ravel()

    all_y = []

    for ax, x_param in zip(axes, params):
        grouped = (
            df.groupby(["Library", x_param], dropna=False)[value_cols]
            .mean(numeric_only=True)
            .reset_index()
            .sort_values([x_param, "Library"])
        )

        
        # DEBUG: Java-WebSocket, ClientCount = 2048
        if x_param == "ClientCount":
            print("\n--- GROUPED DATA CHECK ---")
            print(
                grouped[
                    (grouped["Library"].astype(str).str.strip() == "Java-WebSocket")
                    & (grouped["ClientCount"] == 2048)
                ][[
                    "Library", "ClientCount",
                    "P99_RTT_ms", "P99_Lower_ms", "P99_Upper_ms"
                ]].to_string(index=False)
            )
 
        x_values = sorted(grouped[x_param].dropna().unique())
        x_position = {
            value: i for i, value in enumerate(x_values)
        }

        # Small offsets prevent markers from different libraries
        # from completely overlapping.
        library_span = 0.4
        lib_offsets = {
            lib: (
                (i / max(1, len(libraries) - 1)) - 0.5
            ) * library_span
            for i, lib in enumerate(libraries)
        }

        for library in libraries:
            part = grouped[grouped["Library"] == library].sort_values(
                x_param
            )
            if part.empty:
                continue

            x = part[x_param].map(x_position).to_numpy(dtype=float)
            x_plot = x + lib_offsets[library]
            color = colors[library]

            # P99 lower-upper interval only.
            low = part["P99_Lower_ms"].to_numpy(dtype=float)
            high = part["P99_Upper_ms"].to_numpy(dtype=float)

            valid_interval = (
                np.isfinite(x_plot)
                & np.isfinite(low)
                & np.isfinite(high)
                & (high >= low)
            )
            if args.log_y:
                valid_interval &= (low > 0) & (high > 0)

            if valid_interval.any():
                ax.vlines(
                    x_plot[valid_interval],
                    low[valid_interval],
                    high[valid_interval],
                    color=color,
                    linewidth=1.6,
                    alpha=0.85
                )
                cap_width = 0.025
                ax.hlines(
                    low[valid_interval],
                    x_plot[valid_interval] - cap_width,
                    x_plot[valid_interval] + cap_width,
                    color=color,
                    linewidth=1.1
                )
                ax.hlines(
                    high[valid_interval],
                    x_plot[valid_interval] - cap_width,
                    x_plot[valid_interval] + cap_width,
                    color=color,
                    linewidth=1.1
                )
                all_y.extend(low[valid_interval].tolist())
                all_y.extend(high[valid_interval].tolist())

            # RTT metric markers.
            for metric_label, (col, marker) in METRICS.items():
                y = part[col].to_numpy(dtype=float)
                valid = np.isfinite(x_plot) & np.isfinite(y)

                if args.log_y:
                    valid &= y > 0

                if valid.any():
                    ax.plot(
                        x_plot[valid],
                        y[valid],
                        linestyle="None",
                        marker=marker,
                        markersize=5.5,
                        markerfacecolor=color,
                        markeredgecolor="black",
                        markeredgewidth=0.35,
                        alpha=0.92
                    )
                    all_y.extend(y[valid].tolist())

        
        ax.set_title(x_param, fontsize=12, weight="bold")
        ax.set_xlabel(x_param)
        ax.set_ylabel("RTT (ms)")
        from matplotlib.ticker import MultipleLocator
        ax.yaxis.set_major_locator(MultipleLocator(100))
        ax.grid(True, which="both", alpha=0.22)
        ax.set_axisbelow(True)

        if args.log_y:
            ax.set_yscale("log")

        ticks = list(range(len(x_values)))
        if len(ticks) <= 15:
            ax.set_xticks(ticks, labels=[str(v) for v in x_values])
        else:
            step = max(1, math.ceil(len(ticks) / 15))
            shown = ticks[::step]
            ax.set_xticks(
                shown,
                labels=[str(x_values[i]) for i in shown]
            )
            ax.tick_params(axis="x", labelrotation=35)

    if args.log_y and not args.linear_y:
        positive = [
            v for v in all_y
            if np.isfinite(v) and v > 0
        ]
        if positive:
            lo, hi = min(positive), max(positive)
            for ax in axes:
                ax.set_ylim(lo / 1.25, hi * 1.25)

    metric_handles = [
        Line2D(
            [0], [0],
            marker=marker,
            linestyle="None",
            color="black",
            markerfacecolor="white",
            markeredgecolor="black",
            label=label
        )
        for label, (_, marker) in METRICS.items()
    ]

    bound_handles = [
        Line2D(
            [0], [0],
            color="black",
            marker="|",
            linestyle="None",
            markersize=13,
            markeredgewidth=1.8,
            label="P99_Lower_ms → P99_Upper_ms"
        )
    ]

    library_handles = [
        Line2D(
            [0], [0],
            color=colors[lib],
            linewidth=2,
            label=lib
        )
        for lib in libraries
    ]

    fig.legend(
        handles=metric_handles,
        title="Markers = RTT metrics",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.985),
        ncol=max(1, len(metric_handles)),
        frameon=False
    )
    fig.legend(
        handles=bound_handles,
        title="Vertical intervals = P99 bounds",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.945),
        ncol=1,
        frameon=False
    )
    fig.legend(
        handles=library_handles,
        title="Color = library",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.905),
        ncol=min(4, max(1, len(libraries))),
        frameon=False
    )

    fig.suptitle(
        "RTT metrics across individual parameters\n"
        "Other three parameters averaged for each Library × parameter value",
        fontsize=14,
        y=0.999
    )

    fig.tight_layout(rect=[0.03, 0.03, 0.97, 0.86])

    output_prefix = (
        Path(args.output_prefix)
        if args.output_prefix
        else script_dir / "rtt_parameter_subplots"
    )

    png = Path(f"{output_prefix}.png")
    pdf = Path(f"{output_prefix}.pdf")
    png.parent.mkdir(parents=True, exist_ok=True)
    pdf.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(png, dpi=300, bbox_inches="tight")
    

    print(f"Saved: {png.resolve()}")
    print(f"Saved: {pdf.resolve()}")

    plt.close(fig)


if __name__ == "__main__":
    main()
