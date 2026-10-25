import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 1. Load the dataset
df = pd.read_csv("final_performance_report_averages.csv")

# Map CSV library names to display names
library_mapping = {
    "Java-WebSocket": "Java-WebSocket",
    "Java-Netty": "Java-Netty",
    "Node-ws": "Node.js-ws",
    "node.js-uws": "Node.js-μWebSockets",
    "PHP-Swoole": "PHP-Swoole",
    "go": "Go-gorilla",
    "Python-websockets": "Python-websockets",
}
df["Display_Library"] = df["Library"].map(library_mapping)

libraries = [
    "Java-WebSocket",
    "Java-Netty",
    "Node.js-ws",
    "Node.js-μWebSockets",
    "PHP-Swoole",
    "Go-gorilla",
    "Python-websockets",
]

client_counts = [1, 32, 128, 512, 2048]

# 2. Compute metrics for each library
plot_data = []
actual_fails = []

for lib in libraries:
  sub_df = df[df["Display_Library"] == lib]

  # Real Client Fail (%) average
  client_fail = sub_df["Cli Fail (%)"].mean()
  actual_fails.append(client_fail)

  # Success percentages for each client count tier
  success_tiers = {}
  for cc in client_counts:
    cc_mean = sub_df[sub_df["ClientCount"] == cc]["Cli Success (%)"].mean()
    tier_val = cc_mean / len(client_counts)
    success_tiers[f"Success (Cli-{cc})"] = tier_val

  # Fails by Any Other Reason
  other_fail = max(
      0.0, 100.0 - (client_fail + sum(success_tiers.values()))
  )

  row = {
      "Library": lib,
      "Client Fail": client_fail,
      **success_tiers,
      "Fails by Any Other Reason": other_fail,
  }
  plot_data.append(row)

plot_df = pd.DataFrame(plot_data).set_index("Library").reindex(libraries)

# 3. Plotting the Stacked Bar Chart
fig, ax = plt.subplots(figsize=(12, 7))

colors = [
    "#d9534f",  # Client Fail (Red) - given visual prominence
    "#99d8c4",  # Success (Cli-1)
    "#41ab5d",  # Success (Cli-32)
    "#238443",  # Success (Cli-128)
    "#006837",  # Success (Cli-512)
    "#004529",  # Success (Cli-2048)
    "#3399ff",  # Fails by Any Other Reason (Blue)
]

categories = plot_df.columns.tolist()

# To make the tiny Client Fail bar visible, we use a minimum render height (e.g., 2.0%)
# while preserving the true statistical value in the label text.
visual_plot_df = plot_df.copy()
MIN_VISUAL_HEIGHT = 2.0
visual_plot_df["Client Fail"] = visual_plot_df["Client Fail"].apply(
    lambda x: max(x, MIN_VISUAL_HEIGHT)
)

bottom = np.zeros(len(libraries))

for i, cat in enumerate(categories):
  if cat == "Client Fail":
    values = visual_plot_df[cat].values
  else:
    values = plot_df[cat].values

  ax.bar(
      plot_df.index,
      values,
      bottom=bottom,
      label=cat,
      color=colors[i],
      width=0.7,
  )

  # Add percentage labels
  for j, (val, true_val) in enumerate(
      zip(values, plot_df[cat].values)
  ):
    if cat == "Client Fail":
      # Place the label for Client Fail right above the visible red block
      ax.text(
          j,
          bottom[j] + val + 1.2,
          f"{true_val:.2f}%",
          ha="center",
          va="bottom",
          color="#b30000",
          fontsize=9,
          fontweight="bold",
      )
    elif val > 3.0:
      ax.text(
          j,
          bottom[j] + val / 2,
          f"{val:.1f}%",
          ha="center",
          va="center",
          color=(
              "white" if 0 < i < len(categories) - 1 else "black"
          ),
          fontsize=9,
          fontweight="bold",
      )

  bottom += values

# 4. Chart Styling & Formatting
ax.set_ylabel("Percentage (%)", fontsize=12)
ax.set_ylim(0, 108)  # Expand slightly to fit the bottom annotations
ax.grid(axis="y", linestyle="--", alpha=0.5, color="#d3d3d3")
ax.set_axisbelow(True)

plt.xticks(rotation=25, ha="right", fontsize=11)

# Legend configuration
handles, labels = ax.get_legend_handles_labels()
ax.legend(
    handles,
    labels,
    title="Categories",
    loc="upper center",
    bbox_to_anchor=(0.5, 1.2),
    ncol=4,
    frameon=True,
    fontsize=10,
    title_fontsize=11,
)

plt.tight_layout()
plt.savefig("clifail.png", dpi=300, bbox_inches="tight")
plt.show()