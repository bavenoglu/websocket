
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D

# 1. Load data
df = pd.read_csv("final_performance_report_averages.csv")

mapping = {
    "go": "Go-gorilla",
    "Java-Netty": "Java-Netty",
    "Java-WebSocket": "Java-WebSocket",
    "Node-ws": "Node.js-ws",
    "node.js-uws": "Node.js-μWebSockets",
    "PHP-Swoole": "PHP-Swoole",
    "Python-websockets": "Python-websockets",
}

df["Library"] = df["Library"].map(mapping)

# 2. Calculate average duration
dur_grouped = (
    df.groupby(["Library", "Interval", "ClientCount"])["Duration"]
    .mean()
    .reset_index()
)

dur_grouped["Group"] = (
    "Int: " + dur_grouped["Interval"].astype(str)
    + "\nC: " + dur_grouped["ClientCount"].astype(str)
)

# 3. Expected duration per interval
exp_per_interval = (
    df.groupby("Interval")["Expected Duration"]
    .mean()
)

print("Expected Duration:")
print(exp_per_interval)

# 4. Library configuration
library_order = [
    "Go-gorilla",
    "Java-Netty",
    "Java-WebSocket",
    "Node.js-ws",
    "Node.js-μWebSockets",
    "PHP-Swoole",
    "Python-websockets",
]

colors = [
    "#1f77b4",
    "#ff7f0e",
    "#d62728",
    "#8c564b",
    "#e377c2",
    "#bcbd22",
    "#17becf",
]

palette_dict = dict(zip(library_order, colors))

interval_order = [1, 2, 5, 10]
client_order = [1, 32, 128, 512, 2048]

groups = [
    f"Int: {i}\nC: {c}"
    for i in interval_order
    for c in client_order
]

# 5. Plot
sns.set_theme(style="whitegrid")

fig, ax = plt.subplots(figsize=(22, 8))

sns.barplot(
    data=dur_grouped,
    x="Group",
    y="Duration",
    hue="Library",
    order=groups,
    hue_order=library_order,
    palette=palette_dict,
    ax=ax,
)

# 6. Logarithmic Y axis
ax.set_yscale("log")

# 7. Set Y limits
ymin = min(
    ax.get_ylim()[0],
    exp_per_interval.min() * 0.8
)

ymax = max(
    ax.get_ylim()[1],
    exp_per_interval.max() * 1.2
)

ax.set_ylim(ymin, ymax)

# 8. Expected Duration horizontal lines
group_to_idx = {
    group: idx
    for idx, group in enumerate(groups)
}

for interval in interval_order:

    expected = exp_per_interval.loc[interval]

    interval_groups = [
        g for g in groups
        if g.startswith(f"Int: {interval}\n")
    ]

    x_indices = [
        group_to_idx[g]
        for g in interval_groups
    ]

    xmin = min(x_indices) - 0.5
    xmax = max(x_indices) + 0.5

    ax.plot(
        [xmin, xmax],
        [expected, expected],
        color="#FF1493",
        linestyle="--",
        linewidth=2,
        zorder=1000,
    )

    # Label each reference line
    ax.text(
        xmax - 0.1,
        expected * 1.1,
        f"Expected: {expected:g}s",
        color="black",
        fontsize=8,
        ha="right",
        zorder=1001,
        backgroundcolor="yellow",
    )

# 9. Legend
handles, labels = ax.get_legend_handles_labels()

handles.append(
    Line2D(
        [0], [0],
        color="#FF1493",
        linestyle="--",
        linewidth=3,
        label="Expected Duration",
    )
)

labels.append("Expected Duration")

ax.legend(
    handles,
    labels,
    title="Libraries / Metrics",
    bbox_to_anchor=(0.15, 1.15),
    loc="upper left",
    ncol=8,
    fontsize=11,
    title_fontsize=12,
)

# 10. Labels
#ax.set_title(
#    "Actual Duration vs. Expected Duration",
#    fontsize=15,
#    fontweight="bold",
#    pad=15,
#)

ax.set_xlabel(
    "Interval & Client Count (Int: Interval, C: Client Count)",
    fontsize=13,
    labelpad=10,
)

ax.set_ylabel(
    "Duration (seconds) [Log Scale]",
    fontsize=13,
    labelpad=10,
)

ax.set_xticks(range(len(groups)))
ax.set_xticklabels(
    groups,
    rotation=45,
    ha="right",
    fontsize=10,
)

# 11. Save
plt.tight_layout()

plt.savefig(
    "duration.png",
    dpi=300,
    bbox_inches="tight",
)

print("Saved:", "duration.png")

plt.show()
