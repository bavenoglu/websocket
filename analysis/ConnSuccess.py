import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Load the dataset
df = pd.read_csv('final_performance_report_averages.csv')

# Map technical library names to clean display labels matching benchmark standards
df['Library_Display'] = df['Library'].replace({
    'Node-ws': 'Node.js-ws',
    'node.js-uws': 'Node.js-μWebSockets',
    'go': 'Go-gorilla'
})

library_order = [
    'Go-gorilla',
    'Java-Netty', 
    'Java-WebSocket', 
    'Node.js-ws', 
    'Node.js-μWebSockets', 
    'PHP-Swoole', 
    'Python-websockets'
]

# Color mapping for each library
colors = ['#1f77b4', '#ff7f0e', '#d62728', '#8c564b', '#e377c2', '#bcbd22', '#17becf']
palette = dict(zip(library_order, colors))

# 2. Set up subplots side by side
fig, axes = plt.subplots(1, 4, figsize=(22, 6), sharey=True)

configs = [
    {'col': 'ClientCount', 'xlabel': 'No. of Clients'},
    {'col': 'Interval', 'xlabel': 'Msg Interval (ms)'},
    {'col': 'Timeout', 'xlabel': 'Timeout (ms)'},
    {'col': 'MsgSize', 'xlabel': 'Msg Size', 'custom_labels': {100: '100B', 33000: '33K', 66000: '66K'}}
]

for i, cfg in enumerate(configs):
    ax = axes[i]
    
    # Calculate group averages for Conn_Success_%
    grouped = df.groupby([cfg['col'], 'Library_Display'])['Conn_Success_%'].mean().reset_index()
    
    sns.barplot(
        data=grouped,
        x=cfg['col'],
        y='Conn_Success_%',
        hue='Library_Display',
        hue_order=library_order,
        palette=palette,
        ax=ax,
        edgecolor='black',
        linewidth=0.5
    )
    
    # Format custom X-axis labels where applicable
    if 'custom_labels' in cfg:
        labels = [
            cfg['custom_labels'].get(int(float(t.get_text())), t.get_text()) 
            if t.get_text().replace('.', '', 1).isdigit() else t.get_text() 
            for t in ax.get_xticklabels()
        ]
        ax.set_xticklabels(labels)
        
    # Remove top subplot titles as requested; keep bottom x-labels only
    ax.set_xlabel(cfg['xlabel'], fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel('')
    ax.get_legend().remove()
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Set Y-axis limit and show every 10% increment
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 10))
    ax.yaxis.set_major_formatter(lambda x, pos: f"{int(x)}%")
    
    # Clean spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

# Y-axis label on leftmost plot
axes[0].set_ylabel('Successful Connections (%)', fontsize=12, fontweight='bold')

# 3. Create top centered legend with clean library labels
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles, 
    labels, 
    loc='upper center', 
    bbox_to_anchor=(0.5, 1.02), 
    ncol=len(library_order), 
    frameon=False, 
    fontsize=11
)

# Overall Super Title
fig.suptitle('WebSocket Library', fontsize=15, fontweight='bold', y=1.09)

# Save and show
plt.tight_layout()
plt.savefig('ConnSuccess.png', dpi=300, bbox_inches='tight')
plt.show()