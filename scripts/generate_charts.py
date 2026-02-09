"""
Business Intelligence Analysis: Public Transit Access Impact on Retail Market Locations
Generates visualizations and insights for executive decision-making
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial import distance_matrix
import warnings
warnings.filterwarnings('ignore')

# Set professional styling
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Output directory
OUTPUT_DIR = 'charts/'

print("Loading data...")

# Load market data
markets_df = pd.read_csv('data/combined.csv')

# Load bus data
with open('data/busDetails.json', 'r') as f:
    bus_routes = json.load(f)

with open('data/stops.json', 'r') as f:
    bus_stops = json.load(f)

print(f"Loaded {len(markets_df)} market locations, {len(bus_routes)} bus routes, {len(bus_stops)} bus stops")

# Convert to DataFrames
stops_df = pd.DataFrame(bus_stops)
# Handle mixed decimal formats (both "40.123456" and "40,123,456" exist in data)
# Remove commas (they are thousands separators, not decimal separators)
stops_df['latitude'] = stops_df['latitude'].astype(str).str.replace(',', '').astype(float)
stops_df['longitude'] = stops_df['longitude'].astype(str).str.replace(',', '').astype(float)

print("\nAnalyzing transit accessibility (optimized vectorized calculations)...")

# Vectorized haversine distance calculation
def haversine_vectorized(lat1, lon1, lat2_array, lon2_array):
    """Calculate distance between one point and array of points in km"""
    R = 6371  # Earth radius in km
    lat1, lon1 = np.radians(lat1), np.radians(lon1)
    lat2_array, lon2_array = np.radians(lat2_array), np.radians(lon2_array)

    dlat = lat2_array - lat1
    dlon = lon2_array - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2_array) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# Convert stops to numpy arrays for faster computation
stop_lats = stops_df['latitude'].values
stop_lons = stops_df['longitude'].values

# Calculate distances for all markets (optimized)
print("Calculating distances to nearest bus stops...")
nearest_distances = []
stops_500m = []
stops_1km = []

for idx, market in markets_df.iterrows():
    if idx % 500 == 0:
        print(f"  Processed {idx}/{len(markets_df)} markets...")

    # Calculate all distances at once using vectorized operation
    distances = haversine_vectorized(
        market['latitude'], market['longitude'],
        stop_lats, stop_lons
    )

    nearest_distances.append(np.min(distances))
    stops_500m.append(np.sum(distances <= 0.5))
    stops_1km.append(np.sum(distances <= 1.0))

markets_df['distance_to_nearest_stop'] = nearest_distances
markets_df['stops_within_500m'] = stops_500m
markets_df['stops_within_1km'] = stops_1km

print(f"  Completed all {len(markets_df)} markets!")

# Categorize accessibility
def categorize_accessibility(row):
    if row['stops_within_500m'] >= 3:
        return 'High'
    elif row['stops_within_500m'] >= 1 or row['distance_to_nearest_stop'] <= 0.5:
        return 'Medium'
    else:
        return 'Low'

markets_df['accessibility_level'] = markets_df.apply(categorize_accessibility, axis=1)

print("Generating business intelligence charts...")

# ============================================================================
# CHART 1: Market Accessibility by Transit Proximity
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 7))
accessibility_counts = markets_df['accessibility_level'].value_counts()
colors = {'High': '#2ecc71', 'Medium': '#f39c12', 'Low': '#e74c3c'}
bars = ax.bar(accessibility_counts.index, accessibility_counts.values,
              color=[colors[x] for x in accessibility_counts.index], width=0.6)

ax.set_title('Market Locations by Public Transit Accessibility Level',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Transit Accessibility Level', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of Market Locations', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}\n({height/len(markets_df)*100:.1f}%)',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}01_market_accessibility_overview.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 2: Accessibility by Market Chain
# ============================================================================
fig, ax = plt.subplots(figsize=(14, 8))
chain_accessibility = pd.crosstab(markets_df['chain'], markets_df['accessibility_level'])
chain_accessibility = chain_accessibility[['High', 'Medium', 'Low']]  # Ensure order

chain_accessibility.plot(kind='bar', stacked=False, ax=ax,
                         color=['#2ecc71', '#f39c12', '#e74c3c'], width=0.7)

ax.set_title('Transit Accessibility Comparison Across Market Chains',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Market Chain', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of Locations', fontsize=12, fontweight='bold')
ax.legend(title='Accessibility Level', title_fontsize=11, fontsize=10, loc='upper right')
ax.grid(axis='y', alpha=0.3)
plt.xticks(rotation=0)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}02_accessibility_by_chain.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 3: Market Type vs Transit Access
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 7))
type_accessibility = pd.crosstab(markets_df['type'], markets_df['accessibility_level'], normalize='index') * 100
type_accessibility = type_accessibility[['High', 'Medium', 'Low']]

type_accessibility.plot(kind='bar', stacked=True, ax=ax,
                        color=['#2ecc71', '#f39c12', '#e74c3c'], width=0.7)

ax.set_title('Transit Accessibility Distribution by Store Format',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Store Format', fontsize=12, fontweight='bold')
ax.set_ylabel('Percentage of Locations (%)', fontsize=12, fontweight='bold')
ax.legend(title='Accessibility', title_fontsize=11, fontsize=10, loc='upper right')
ax.grid(axis='y', alpha=0.3)
plt.xticks(rotation=45, ha='right')
ax.set_ylim([0, 100])

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}03_accessibility_by_store_format.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 4: Average Transit Proximity by Chain
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 7))
chain_avg_distance = markets_df.groupby('chain')['distance_to_nearest_stop'].mean().sort_values()

bars = ax.barh(chain_avg_distance.index, chain_avg_distance.values,
               color='#3498db', height=0.6)

ax.set_title('Average Distance to Nearest Bus Stop by Market Chain',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Average Distance (kilometers)', fontsize=12, fontweight='bold')
ax.set_ylabel('Market Chain', fontsize=12, fontweight='bold')
ax.grid(axis='x', alpha=0.3)

# Add value labels
for i, (idx, val) in enumerate(chain_avg_distance.items()):
    ax.text(val + 0.01, i, f'{val:.2f} km', va='center', fontsize=10, fontweight='bold')

# Add reference line at 500m (walking distance)
ax.axvline(x=0.5, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Walking Distance (500m)')
ax.legend(fontsize=10)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}04_avg_distance_by_chain.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 5: Distribution of Bus Stop Density Near Markets
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 7))

# Create bins for stop counts
stop_bins = [0, 1, 3, 5, 10, 50]
stop_labels = ['0 stops', '1-2 stops', '3-4 stops', '5-9 stops', '10+ stops']
markets_df['stops_category'] = pd.cut(markets_df['stops_within_500m'],
                                       bins=stop_bins, labels=stop_labels, right=False)

stop_distribution = markets_df['stops_category'].value_counts().sort_index()

bars = ax.bar(range(len(stop_distribution)), stop_distribution.values,
              color='#9b59b6', width=0.7)

ax.set_title('Number of Bus Stops Within 500m Walking Distance of Markets',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Bus Stop Density', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of Market Locations', fontsize=12, fontweight='bold')
ax.set_xticks(range(len(stop_distribution)))
ax.set_xticklabels(stop_distribution.index, rotation=0)
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}05_bus_stop_density_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 6: Chain Market Share by Accessibility Level
# ============================================================================
fig, ax = plt.subplots(figsize=(14, 8))

accessibility_chain = pd.crosstab(markets_df['accessibility_level'], markets_df['chain'], normalize='index') * 100
accessibility_chain = accessibility_chain.reindex(['High', 'Medium', 'Low'])

accessibility_chain.plot(kind='bar', ax=ax, width=0.75)

ax.set_title('Market Chain Share Within Each Accessibility Level',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Transit Accessibility Level', fontsize=12, fontweight='bold')
ax.set_ylabel('Market Share (%)', fontsize=12, fontweight='bold')
ax.legend(title='Market Chain', title_fontsize=11, fontsize=10, loc='upper right')
ax.grid(axis='y', alpha=0.3)
plt.xticks(rotation=0)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}06_chain_share_by_accessibility.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 7: Transit Access vs Store Format Count
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 7))

format_counts = markets_df.groupby(['type', 'accessibility_level']).size().unstack(fill_value=0)
format_counts = format_counts[['High', 'Medium', 'Low']]
format_counts = format_counts.sort_values('High', ascending=True)

format_counts.plot(kind='barh', stacked=False, ax=ax,
                   color=['#2ecc71', '#f39c12', '#e74c3c'], width=0.7)

ax.set_title('Store Format Distribution Across Transit Accessibility Levels',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Number of Locations', fontsize=12, fontweight='bold')
ax.set_ylabel('Store Format', fontsize=12, fontweight='bold')
ax.legend(title='Accessibility', title_fontsize=11, fontsize=10, loc='lower right')
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}07_format_distribution_by_accessibility.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 8: High Accessibility Locations by Chain (Competitive Analysis)
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 7))

high_access_markets = markets_df[markets_df['accessibility_level'] == 'High']
chain_high_access = high_access_markets['chain'].value_counts()

bars = ax.bar(chain_high_access.index, chain_high_access.values,
              color='#27ae60', width=0.6)

ax.set_title('Market Chains Commanding High-Accessibility Transit Locations',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Market Chain', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of High-Accessibility Locations', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}08_high_accessibility_chain_leaders.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 9: Transit Coverage Gap Analysis
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 7))

low_access_markets = markets_df[markets_df['accessibility_level'] == 'Low']
chain_low_access = low_access_markets['chain'].value_counts().sort_values(ascending=True)

bars = ax.barh(chain_low_access.index, chain_low_access.values,
               color='#e74c3c', height=0.6)

ax.set_title('Market Locations with Poor Transit Access (Expansion Risk)',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Number of Low-Accessibility Locations', fontsize=12, fontweight='bold')
ax.set_ylabel('Market Chain', fontsize=12, fontweight='bold')
ax.grid(axis='x', alpha=0.3)

# Add value labels
for i, (idx, val) in enumerate(chain_low_access.items()):
    ax.text(val + 0.5, i, f'{int(val)}', va='center', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}09_transit_coverage_gaps_by_chain.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 10: Average Transit Stop Density by Chain
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 7))

chain_avg_stops = markets_df.groupby('chain')['stops_within_500m'].mean().sort_values(ascending=False)

bars = ax.bar(chain_avg_stops.index, chain_avg_stops.values,
              color='#1abc9c', width=0.6)

ax.set_title('Average Number of Bus Stops Within 500m by Market Chain',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Market Chain', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Number of Bus Stops', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}10_avg_stop_density_by_chain.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# Generate Summary Statistics
# ============================================================================
print("\n" + "="*70)
print("BUSINESS INSIGHTS SUMMARY")
print("="*70)

total_markets = len(markets_df)
high_access = len(markets_df[markets_df['accessibility_level'] == 'High'])
medium_access = len(markets_df[markets_df['accessibility_level'] == 'Medium'])
low_access = len(markets_df[markets_df['accessibility_level'] == 'Low'])

print(f"\nTotal Market Locations Analyzed: {total_markets}")
print(f"  - High Accessibility:   {high_access} ({high_access/total_markets*100:.1f}%)")
print(f"  - Medium Accessibility: {medium_access} ({medium_access/total_markets*100:.1f}%)")
print(f"  - Low Accessibility:    {low_access} ({low_access/total_markets*100:.1f}%)")

print("\nChain Performance:")
for chain in markets_df['chain'].unique():
    chain_data = markets_df[markets_df['chain'] == chain]
    high_pct = len(chain_data[chain_data['accessibility_level'] == 'High']) / len(chain_data) * 100
    avg_dist = chain_data['distance_to_nearest_stop'].mean()
    print(f"  {chain}: {high_pct:.1f}% high-access locations, {avg_dist:.2f}km avg distance")

print("\nStore Format Analysis:")
for store_type in ['Hiper', 'Super', 'Market', 'Ekspres']:
    if store_type in markets_df['type'].values:
        type_data = markets_df[markets_df['type'] == store_type]
        high_pct = len(type_data[type_data['accessibility_level'] == 'High']) / len(type_data) * 100
        print(f"  {store_type}: {high_pct:.1f}% have high transit access")

print("\nKey Metrics:")
print(f"  - Average distance to nearest stop: {markets_df['distance_to_nearest_stop'].mean():.2f} km")
print(f"  - Average stops within 500m: {markets_df['stops_within_500m'].mean():.1f}")
print(f"  - Markets with 0 nearby stops: {len(markets_df[markets_df['stops_within_500m'] == 0])}")
print(f"  - Markets with 5+ nearby stops: {len(markets_df[markets_df['stops_within_500m'] >= 5])}")

print("\n" + "="*70)
print("All charts successfully generated in charts/ directory")
print("="*70)
