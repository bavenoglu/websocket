import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- Style ---
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 300
})

# --- Load ---
df = pd.read_csv("final_performance_report_averages.csv")
df.columns = df.columns.str.strip()
order = ["Java-WebSocket", "Java-Netty", "Node-ws", "node.js-uws", "PHP-Swoole", "go", "Python-websockets"]
# --- Library labels for display ---
library_labels = {
    "Java-WebSocket": "Java-WebSocket",
    "Java-Netty": "Java-Netty",
    "Node-ws": "Node.js-ws",
    "node.js-uws": "Node.js-µWebSockets",
    "PHP-Swoole": "PHP-Swoole",
    "go": "Go-gorilla",
    "Python-websockets": "Python-websockets"
}

# --- Columns ---
group_col = "Library"
x_col = "ClientCount"
metrics = ["Client_Log_Count", "Absent_Cli_Msg", "Unconn_Lost_msg"]

# --- Aggregate ---
summary = df.groupby([group_col, x_col])[metrics].sum()

# --- Full grid ---
#libraries = sorted(df[group_col].unique())
libraries = [lib for lib in order if lib in df[group_col].unique()]
clients = sorted(df[x_col].unique())

full_index = pd.MultiIndex.from_product(
    [libraries, clients],
    names=[group_col, x_col]
)

summary = summary.reindex(full_index, fill_value=0).reset_index()

# --- Convert to percentages ---
summary["Total"] = summary[metrics].sum(axis=1)

for m in metrics:
    summary[m] = np.where(
        summary["Total"] > 0,
        summary[m] / summary["Total"] * 100,
        0
    )

# --- Plot ---
fig, ax = plt.subplots(figsize=(14, 5))

bar_width = 0.6
group_spacing = 1.5

x_positions = []
x_labels = []
current_x = 0

colors = {
    "Client_Log_Count": "#4C72B0",
    "Absent_Cli_Msg": "#DD8452",
    "Unconn_Lost_msg": "#55A868"
}

for lib in libraries:
    lib_data = summary[summary[group_col] == lib]
    group_start = current_x

    for c in clients:
        row = lib_data[lib_data[x_col] == c].iloc[0]

        bottom = 0
        for key in metrics:
            value = row[key]

            ax.bar(
                current_x,
                value,
                bar_width,
                bottom=bottom,
                color=colors[key],
                edgecolor='black',
                linewidth=0.4,
                label=key if current_x == 0 else ""
            )

            # --- Orange labels (Failed Messages) ---
            if key == "Absent_Cli_Msg" and value > 1:
                ax.text(
                    current_x,
                    bottom + value / 2,
                    f"{value:.1f}%",
                    ha='center',
                    va='center',
                    fontsize=7,
                    color='black'
                )

            # --- Green labels (Lost Messages) ---
            if key == "Unconn_Lost_msg" and value > 1:
                ax.text(
                    current_x,
                    bottom + value / 2,
                    f"{value:.1f}%",
                    ha='center',
                    va='center',
                    fontsize=7,
                    color='black'  # better contrast on green
                )

            bottom += value

        x_positions.append(current_x)
        x_labels.append(str(int(c)))
        current_x += 1

    # --- Library label ---
    group_end = current_x - 1
    center = (group_start + group_end) / 2

    display_label = library_labels.get(lib, lib)

    ax.text(
        center, -0.15, display_label,
        transform=ax.get_xaxis_transform(),
        ha='center', va='top',
        fontsize=9, fontweight='bold'
    )

    current_x += group_spacing

# --- X axis ---
ax.set_xticks(x_positions)
ax.set_xticklabels(x_labels, rotation=30, ha='right')

# --- Y axis ---
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 10))
ax.set_yticklabels([f"{i}%" for i in range(0, 101, 10)])
ax.set_ylabel("Message Distribution (%)")

# --- Grid ---
ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.6)

# --- Clean look ---
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# --- Legend ---
handles, labels = ax.get_legend_handles_labels()

new_labels = [
    "Successful Message Delivery",
    "Failed Message Delivery (Connected Clients)",
    "Message Loss Due to Connection Failure"
]

ax.legend(handles, new_labels,
          loc='upper center',
          bbox_to_anchor=(0.5, 1.15),
          ncol=3,
          frameon=False)

# --- Save ---
plt.tight_layout()
plt.savefig("messagepercent.png", bbox_inches='tight')

plt.show()