#!/usr/bin/env python3
"""
Bank of Baku — Business Intelligence Analysis
Analyzes bank branch locations against Baku's public transport network
to surface competitive positioning, accessibility gaps, and expansion opportunities.
"""

import json
import csv
import math
import os
from collections import Counter, defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
CHARTS_DIR = "charts"
DATA_DIR = "data"
BRANCHES_FILE = os.path.join(DATA_DIR, "branches", "combined_branches.csv")
STOPS_FILE = os.path.join(DATA_DIR, "stops.json")
BUS_DETAILS_FILE = os.path.join(DATA_DIR, "busDetails.json")

BOB = "Bank of Baku"
HIGHLIGHT_COLOR = "#1B4F72"      # Dark blue for BOB
COMPETITOR_COLOR = "#AEB6BF"     # Grey for competitors
ACCENT_COLOR = "#E74C3C"         # Red for alerts / opportunity
POSITIVE_COLOR = "#27AE60"       # Green for positive
SECONDARY_COLOR = "#F39C12"      # Orange for secondary highlights
PALETTE = [
    "#1B4F72", "#2E86C1", "#AED6F1", "#F39C12", "#E74C3C",
    "#27AE60", "#8E44AD", "#E67E22", "#1ABC9C", "#C0392B",
    "#7F8C8D", "#2C3E50", "#D4AC0D", "#6C3483", "#117A65",
    "#CA6F1E", "#5D6D7E", "#A93226", "#1A5276", "#B7950B"
]

# Baku central area bounds (approximate)
BAKU_CENTER = {"lat_min": 40.35, "lat_max": 40.45, "lon_min": 49.78, "lon_max": 49.98}
# Greater Baku area
BAKU_GREATER = {"lat_min": 40.30, "lat_max": 40.65, "lon_min": 49.65, "lon_max": 50.20}

# Distance thresholds in meters
WALKING_DISTANCE = 400     # ~5 min walk
CLOSE_DISTANCE = 300
MEDIUM_DISTANCE = 600


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two lat/lon points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def safe_float(val):
    """Parse a coordinate string, returning None if invalid."""
    try:
        v = float(val)
        if 30 < v < 55:
            return v
        return None
    except (ValueError, TypeError):
        return None


def style_chart(ax, title, xlabel="", ylabel="", rotate_x=0):
    """Apply consistent business styling to a chart."""
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15, color="#2C3E50")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11, color="#2C3E50")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11, color="#2C3E50")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#BDC3C7')
    ax.spines['bottom'].set_color('#BDC3C7')
    ax.tick_params(colors='#2C3E50', labelsize=9)
    if rotate_x:
        plt.xticks(rotation=rotate_x, ha='right')
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)


# ──────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────
def load_data():
    print("Loading data...")

    # Branches
    branches = []
    with open(BRANCHES_FILE, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            lat = safe_float(row['lat'])
            lon = safe_float(row['long'])
            if lat and lon:
                branches.append({"bank": row['bank_name'], "lat": lat, "lon": lon})
    print(f"  Branches: {len(branches)}")

    # Stops
    with open(STOPS_FILE, 'r', encoding='utf-8') as f:
        raw_stops = json.load(f)
    stops = []
    for s in raw_stops:
        lat = safe_float(s.get('latitude'))
        lon = safe_float(s.get('longitude'))
        if lat and lon:
            stops.append({
                "id": s['id'],
                "lat": lat,
                "lon": lon,
                "hub": s.get('isTransportHub', False)
            })
    print(f"  Stops (valid coords): {len(stops)}")

    # Bus details
    with open(BUS_DETAILS_FILE, 'r', encoding='utf-8') as f:
        buses = json.load(f)
    print(f"  Bus routes: {len(buses)}")

    # Build stop-route index: how many routes serve each stop
    stop_route_count = Counter()
    stop_coords_from_bus = {}
    for b in buses:
        for s in b.get('stops', []):
            sid = s.get('stopId')
            stop_route_count[sid] += 1
            if s.get('stop'):
                lat = safe_float(s['stop'].get('latitude'))
                lon = safe_float(s['stop'].get('longitude'))
                if lat and lon:
                    stop_coords_from_bus[sid] = (lat, lon)

    # Enrich stops with route counts
    stop_id_set = {s['id'] for s in stops}
    for s in stops:
        s['routes'] = stop_route_count.get(s['id'], 0)

    print(f"  Stops served by at least 1 route: {sum(1 for s in stops if s['routes'] > 0)}")
    print(f"  Transport hubs: {sum(1 for s in stops if s['hub'])}")

    return branches, stops, buses, stop_route_count


# ──────────────────────────────────────────────
# Analysis Functions
# ──────────────────────────────────────────────
def branches_by_bank(branches):
    """Count branches per bank."""
    counts = Counter(b['bank'] for b in branches)
    return counts.most_common()


def classify_location(lat, lon):
    """Classify a coordinate as Baku Center, Greater Baku, or Regional."""
    if (BAKU_CENTER['lat_min'] <= lat <= BAKU_CENTER['lat_max'] and
            BAKU_CENTER['lon_min'] <= lon <= BAKU_CENTER['lon_max']):
        return "Baku Center"
    elif (BAKU_GREATER['lat_min'] <= lat <= BAKU_GREATER['lat_max'] and
          BAKU_GREATER['lon_min'] <= lon <= BAKU_GREATER['lon_max']):
        return "Greater Baku"
    else:
        return "Regional"


def compute_accessibility(branches, stops, threshold=WALKING_DISTANCE):
    """For each branch, count bus stops within threshold distance."""
    results = []
    for br in branches:
        nearby = 0
        total_routes = 0
        nearest_stop_dist = float('inf')
        for s in stops:
            d = haversine(br['lat'], br['lon'], s['lat'], s['lon'])
            if d < nearest_stop_dist:
                nearest_stop_dist = d
            if d <= threshold:
                nearby += 1
                total_routes += s['routes']
        results.append({
            "bank": br['bank'],
            "lat": br['lat'],
            "lon": br['lon'],
            "nearby_stops": nearby,
            "nearby_routes": total_routes,
            "nearest_stop_m": nearest_stop_dist
        })
    return results


def compute_hub_proximity(branches, stops):
    """Distance from each branch to nearest transport hub."""
    hubs = [s for s in stops if s['hub']]
    results = []
    for br in branches:
        min_dist = float('inf')
        for h in hubs:
            d = haversine(br['lat'], br['lon'], h['lat'], h['lon'])
            if d < min_dist:
                min_dist = d
        results.append({
            "bank": br['bank'],
            "lat": br['lat'],
            "lon": br['lon'],
            "hub_distance_m": min_dist
        })
    return results


def find_competitor_gaps(branches, stops, bob_name=BOB):
    """Find high-traffic stops that have competitor branches nearby but no BOB."""
    bob_branches = [b for b in branches if b['bank'] == bob_name]
    competitor_branches = [b for b in branches if b['bank'] != bob_name]

    # Focus on high-traffic stops (10+ routes)
    high_traffic = [s for s in stops if s['routes'] >= 10]

    gaps = []
    for s in high_traffic:
        # Check if any BOB branch within 600m
        bob_nearby = any(
            haversine(s['lat'], s['lon'], b['lat'], b['lon']) <= MEDIUM_DISTANCE
            for b in bob_branches
        )
        # Count competitor branches within 600m
        comp_nearby = sum(
            1 for b in competitor_branches
            if haversine(s['lat'], s['lon'], b['lat'], b['lon']) <= MEDIUM_DISTANCE
        )
        if not bob_nearby and comp_nearby > 0:
            gaps.append({
                "stop_id": s['id'],
                "lat": s['lat'],
                "lon": s['lon'],
                "routes": s['routes'],
                "competitors_nearby": comp_nearby,
                "hub": s['hub']
            })

    return sorted(gaps, key=lambda x: (-x['routes'], -x['competitors_nearby']))


def compute_competitive_overlap(branches, bob_name=BOB):
    """For each BOB branch, count competitor branches within 500m."""
    bob_branches = [b for b in branches if b['bank'] == bob_name]
    others = [b for b in branches if b['bank'] != bob_name]

    results = []
    for bb in bob_branches:
        nearby_competitors = defaultdict(int)
        for o in others:
            d = haversine(bb['lat'], bb['lon'], o['lat'], o['lon'])
            if d <= 500:
                nearby_competitors[o['bank']] += 1
        results.append({
            "lat": bb['lat'],
            "lon": bb['lon'],
            "total_competitors": sum(nearby_competitors.values()),
            "competitor_banks": dict(nearby_competitors)
        })
    return results


def zone_coverage_analysis(branches):
    """Analyze geographic distribution of branches per bank."""
    bank_zones = defaultdict(lambda: Counter())
    for b in branches:
        zone = classify_location(b['lat'], b['lon'])
        bank_zones[b['bank']][zone] += 1
    return bank_zones


# ──────────────────────────────────────────────
# Chart Generation
# ──────────────────────────────────────────────
def chart_01_market_position(branch_counts):
    """Chart 1: Branch Network Size — All Banks"""
    fig, ax = plt.subplots(figsize=(14, 7))

    banks = [b[0] for b in branch_counts]
    counts = [b[1] for b in branch_counts]
    colors = [HIGHLIGHT_COLOR if b == BOB else COMPETITOR_COLOR for b in banks]

    bars = ax.barh(range(len(banks)), counts, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(banks)))
    ax.set_yticklabels(banks, fontsize=10)
    ax.invert_yaxis()

    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                str(count), va='center', fontsize=10, fontweight='bold',
                color=HIGHLIGHT_COLOR if banks[i] == BOB else '#555')

    style_chart(ax, "Branch Network Size by Bank", xlabel="Number of Branches")
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.yaxis.grid(False)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "01_market_position.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 01: Market Position")


def chart_02_geographic_distribution(bank_zones, branch_counts):
    """Chart 2: Geographic Distribution — Baku Center vs Greater Baku vs Regional"""
    top_banks = [b[0] for b in branch_counts[:12]]
    zones = ["Baku Center", "Greater Baku", "Regional"]
    zone_colors = ["#1B4F72", "#2E86C1", "#AED6F1"]

    fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(top_banks))
    width = 0.65
    bottoms = np.zeros(len(top_banks))

    for i, zone in enumerate(zones):
        values = [bank_zones[bank][zone] for bank in top_banks]
        bars = ax.bar(x, values, width, bottom=bottoms, label=zone,
                      color=zone_colors[i], edgecolor='white', linewidth=0.5)
        # Add value labels for non-zero segments
        for j, v in enumerate(values):
            if v > 0:
                ax.text(x[j], bottoms[j] + v / 2, str(v),
                        ha='center', va='center', fontsize=8, fontweight='bold', color='white')
        bottoms += np.array(values)

    ax.set_xticks(x)
    ax.set_xticklabels(top_banks, fontsize=9)
    style_chart(ax, "Geographic Distribution of Branches", ylabel="Number of Branches", rotate_x=35)
    ax.legend(loc='upper right', framealpha=0.9)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "02_geographic_distribution.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 02: Geographic Distribution")


def chart_03_bob_vs_top5_geo(bank_zones, branch_counts):
    """Chart 3: BOB Geographic Mix vs Top 5 Competitors"""
    top5 = [b[0] for b in branch_counts[:6] if b[0] != BOB][:5]
    banks_to_show = [BOB] + top5
    zones = ["Baku Center", "Greater Baku", "Regional"]

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(banks_to_show))
    width = 0.65
    bottoms = np.zeros(len(banks_to_show))
    zone_colors = [HIGHLIGHT_COLOR, "#2E86C1", SECONDARY_COLOR]

    for i, zone in enumerate(zones):
        totals = [sum(bank_zones[bank].values()) for bank in banks_to_show]
        values = [bank_zones[bank][zone] / total * 100 if total > 0 else 0
                  for bank, total in zip(banks_to_show, totals)]
        bars = ax.bar(x, values, width, bottom=bottoms, label=zone,
                      color=zone_colors[i], edgecolor='white', linewidth=0.5)
        for j, v in enumerate(values):
            if v > 5:
                ax.text(x[j], bottoms[j] + v / 2, f"{v:.0f}%",
                        ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        bottoms += np.array(values)

    ax.set_xticks(x)
    ax.set_xticklabels(banks_to_show, fontsize=10)
    ax.set_ylim(0, 105)
    style_chart(ax, "Geographic Mix: BOB vs Top 5 Competitors (% of Branches)",
                ylabel="% of Total Branches", rotate_x=20)
    ax.legend(loc='upper right', framealpha=0.9)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "03_bob_vs_top5_geographic.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 03: BOB vs Top5 Geographic Mix")


def chart_04_transit_accessibility(accessibility, branch_counts):
    """Chart 4: Average Bus Stops within Walking Distance per Branch"""
    top_banks = [b[0] for b in branch_counts[:15]]

    bank_avg = {}
    for bank in top_banks:
        bank_data = [a for a in accessibility if a['bank'] == bank]
        if bank_data:
            bank_avg[bank] = sum(a['nearby_stops'] for a in bank_data) / len(bank_data)

    sorted_banks = sorted(bank_avg.items(), key=lambda x: -x[1])
    banks = [b[0] for b in sorted_banks]
    avgs = [b[1] for b in sorted_banks]
    colors = [HIGHLIGHT_COLOR if b == BOB else COMPETITOR_COLOR for b in banks]

    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.barh(range(len(banks)), avgs, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(banks)))
    ax.set_yticklabels(banks, fontsize=10)
    ax.invert_yaxis()

    for i, (bar, avg) in enumerate(zip(bars, avgs)):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{avg:.1f}", va='center', fontsize=10, fontweight='bold',
                color=HIGHLIGHT_COLOR if banks[i] == BOB else '#555')

    style_chart(ax, f"Average Bus Stops Within {WALKING_DISTANCE}m of Each Branch",
                xlabel="Avg. Number of Bus Stops")
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.yaxis.grid(False)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "04_transit_accessibility.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 04: Transit Accessibility")


def chart_05_route_connectivity(accessibility, branch_counts):
    """Chart 5: Average Bus Routes Reachable within Walking Distance"""
    top_banks = [b[0] for b in branch_counts[:15]]

    bank_avg = {}
    for bank in top_banks:
        bank_data = [a for a in accessibility if a['bank'] == bank]
        if bank_data:
            bank_avg[bank] = sum(a['nearby_routes'] for a in bank_data) / len(bank_data)

    sorted_banks = sorted(bank_avg.items(), key=lambda x: -x[1])
    banks = [b[0] for b in sorted_banks]
    avgs = [b[1] for b in sorted_banks]
    colors = [HIGHLIGHT_COLOR if b == BOB else COMPETITOR_COLOR for b in banks]

    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.barh(range(len(banks)), avgs, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(banks)))
    ax.set_yticklabels(banks, fontsize=10)
    ax.invert_yaxis()

    for i, (bar, avg) in enumerate(zip(bars, avgs)):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{avg:.0f}", va='center', fontsize=10, fontweight='bold',
                color=HIGHLIGHT_COLOR if banks[i] == BOB else '#555')

    style_chart(ax, f"Average Bus Routes Reachable Within {WALKING_DISTANCE}m of Each Branch",
                xlabel="Avg. Number of Bus Routes")
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.yaxis.grid(False)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "05_route_connectivity.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 05: Route Connectivity")


def chart_06_hub_proximity(hub_data, branch_counts):
    """Chart 6: Average Distance to Nearest Transport Hub"""
    top_banks = [b[0] for b in branch_counts[:15]]

    # Only consider Baku-area branches (where hubs are)
    bank_avg = {}
    for bank in top_banks:
        baku_branches = [h for h in hub_data if h['bank'] == bank and
                         BAKU_GREATER['lat_min'] <= h['lat'] <= BAKU_GREATER['lat_max'] and
                         BAKU_GREATER['lon_min'] <= h['lon'] <= BAKU_GREATER['lon_max']]
        if baku_branches:
            bank_avg[bank] = sum(h['hub_distance_m'] for h in baku_branches) / len(baku_branches)

    sorted_banks = sorted(bank_avg.items(), key=lambda x: x[1])
    banks = [b[0] for b in sorted_banks]
    avgs = [b[1] for b in sorted_banks]
    colors = [HIGHLIGHT_COLOR if b == BOB else COMPETITOR_COLOR for b in banks]

    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.barh(range(len(banks)), avgs, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(banks)))
    ax.set_yticklabels(banks, fontsize=10)
    ax.invert_yaxis()

    for i, (bar, avg) in enumerate(zip(bars, avgs)):
        ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height() / 2,
                f"{avg:.0f}m", va='center', fontsize=10, fontweight='bold',
                color=HIGHLIGHT_COLOR if banks[i] == BOB else '#555')

    style_chart(ax, "Average Distance to Nearest Transport Hub (Baku Branches Only)",
                xlabel="Distance (meters)")
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.yaxis.grid(False)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "06_hub_proximity.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 06: Hub Proximity")


def chart_07_bob_branch_scorecard(accessibility):
    """Chart 7: BOB Individual Branch Accessibility Scorecard"""
    bob_data = [a for a in accessibility if a['bank'] == BOB]
    bob_data.sort(key=lambda x: -x['nearby_routes'])

    labels = [f"({a['lat']:.3f}, {a['lon']:.3f})" for a in bob_data]
    # Classify
    zones = [classify_location(a['lat'], a['lon']) for a in bob_data]
    short_labels = []
    zone_counter = Counter()
    for z in zones:
        zone_counter[z] += 1
        short_labels.append(f"{z[:3]}#{zone_counter[z]}")

    routes = [a['nearby_routes'] for a in bob_data]
    stops_count = [a['nearby_stops'] for a in bob_data]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Routes
    colors_r = [POSITIVE_COLOR if r >= 50 else (SECONDARY_COLOR if r >= 20 else ACCENT_COLOR)
                for r in routes]
    ax1.barh(range(len(short_labels)), routes, color=colors_r, edgecolor='white', linewidth=0.5)
    ax1.set_yticks(range(len(short_labels)))
    ax1.set_yticklabels(short_labels, fontsize=9)
    ax1.invert_yaxis()
    for i, v in enumerate(routes):
        ax1.text(v + 1, i, str(v), va='center', fontsize=9, fontweight='bold')
    style_chart(ax1, f"Bus Routes Within {WALKING_DISTANCE}m", xlabel="Number of Routes")
    ax1.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax1.yaxis.grid(False)

    # Stops
    colors_s = [POSITIVE_COLOR if s >= 10 else (SECONDARY_COLOR if s >= 5 else ACCENT_COLOR)
                for s in stops_count]
    ax2.barh(range(len(short_labels)), stops_count, color=colors_s, edgecolor='white', linewidth=0.5)
    ax2.set_yticks(range(len(short_labels)))
    ax2.set_yticklabels(short_labels, fontsize=9)
    ax2.invert_yaxis()
    for i, v in enumerate(stops_count):
        ax2.text(v + 0.3, i, str(v), va='center', fontsize=9, fontweight='bold')
    style_chart(ax2, f"Bus Stops Within {WALKING_DISTANCE}m", xlabel="Number of Stops")
    ax2.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax2.yaxis.grid(False)

    fig.suptitle("Bank of Baku — Branch-Level Public Transit Scorecard",
                 fontsize=15, fontweight='bold', color="#2C3E50", y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "07_bob_branch_scorecard.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 07: BOB Branch Scorecard")


def chart_08_expansion_opportunities(gaps):
    """Chart 8: Top Expansion Opportunities — High-Traffic Stops Without BOB"""
    top_gaps = gaps[:20]
    if not top_gaps:
        print("  Chart 08: Skipped (no gaps found)")
        return

    fig, ax = plt.subplots(figsize=(14, 8))

    labels = [f"Stop {g['stop_id']} ({g['lat']:.3f}, {g['lon']:.3f})" for g in top_gaps]
    routes = [g['routes'] for g in top_gaps]
    competitors = [g['competitors_nearby'] for g in top_gaps]

    x = np.arange(len(labels))
    width = 0.35

    bars1 = ax.bar(x - width / 2, routes, width, label='Bus Routes at Stop',
                   color=HIGHLIGHT_COLOR, edgecolor='white', linewidth=0.5)
    bars2 = ax.bar(x + width / 2, competitors, width, label='Competitor Branches Nearby',
                   color=ACCENT_COLOR, edgecolor='white', linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    style_chart(ax, "Top 20 Expansion Opportunities: High-Traffic Stops Without BOB Presence",
                ylabel="Count", rotate_x=55)
    ax.legend(loc='upper right', framealpha=0.9)

    # Add hub markers
    for i, g in enumerate(top_gaps):
        if g['hub']:
            ax.annotate('HUB', (i, routes[i]), fontsize=7, fontweight='bold',
                        ha='center', va='bottom', color=ACCENT_COLOR)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "08_expansion_opportunities.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 08: Expansion Opportunities")


def chart_09_competitive_pressure(overlap_data):
    """Chart 9: Competitive Pressure on Each BOB Branch"""
    overlap_data.sort(key=lambda x: -x['total_competitors'])

    labels = [f"({o['lat']:.3f}, {o['lon']:.3f})" for o in overlap_data]
    totals = [o['total_competitors'] for o in overlap_data]

    # Get all competitor banks that appear
    all_comp_banks = set()
    for o in overlap_data:
        all_comp_banks.update(o['competitor_banks'].keys())
    all_comp_banks = sorted(all_comp_banks)

    fig, ax = plt.subplots(figsize=(14, 8))

    x = np.arange(len(labels))
    bottoms = np.zeros(len(labels))
    color_map = {bank: PALETTE[i % len(PALETTE)] for i, bank in enumerate(all_comp_banks)}

    for bank in all_comp_banks:
        values = [o['competitor_banks'].get(bank, 0) for o in overlap_data]
        if sum(values) > 0:
            ax.bar(x, values, bottom=bottoms, label=bank,
                   color=color_map[bank], edgecolor='white', linewidth=0.3, width=0.7)
            bottoms += np.array(values)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    style_chart(ax, "Competitive Pressure: Competitor Branches Within 500m of Each BOB Location",
                ylabel="Number of Competitor Branches", rotate_x=55)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=7, ncol=1)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "09_competitive_pressure.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 09: Competitive Pressure")


def chart_10_nearest_stop_distribution(accessibility, branch_counts):
    """Chart 10: Distribution of Nearest Bus Stop Distance"""
    top_banks = [b[0] for b in branch_counts[:10]]

    fig, ax = plt.subplots(figsize=(14, 7))

    bank_medians = {}
    for bank in top_banks:
        dists = sorted([a['nearest_stop_m'] for a in accessibility if a['bank'] == bank])
        if dists:
            bank_medians[bank] = dists[len(dists) // 2]

    sorted_banks = sorted(bank_medians.items(), key=lambda x: x[1])
    banks = [b[0] for b in sorted_banks]
    medians = [b[1] for b in sorted_banks]
    colors = [HIGHLIGHT_COLOR if b == BOB else COMPETITOR_COLOR for b in banks]

    bars = ax.barh(range(len(banks)), medians, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(banks)))
    ax.set_yticklabels(banks, fontsize=10)
    ax.invert_yaxis()

    for i, (bar, med) in enumerate(zip(bars, medians)):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2,
                f"{med:.0f}m", va='center', fontsize=10, fontweight='bold',
                color=HIGHLIGHT_COLOR if banks[i] == BOB else '#555')

    style_chart(ax, "Median Distance to Nearest Bus Stop (Top 10 Banks)",
                xlabel="Distance (meters)")
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.yaxis.grid(False)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "10_nearest_stop_distance.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 10: Nearest Stop Distribution")


def chart_11_baku_center_density(branches, stops):
    """Chart 11: Branch Density in Baku Center vs Transit Stop Density"""
    center_stops = [s for s in stops
                    if BAKU_CENTER['lat_min'] <= s['lat'] <= BAKU_CENTER['lat_max'] and
                    BAKU_CENTER['lon_min'] <= s['lon'] <= BAKU_CENTER['lon_max']]

    # Divide Baku center into a 5x5 grid
    lat_bins = np.linspace(BAKU_CENTER['lat_min'], BAKU_CENTER['lat_max'], 6)
    lon_bins = np.linspace(BAKU_CENTER['lon_min'], BAKU_CENTER['lon_max'], 6)

    # Count BOB branches, competitor branches, and stops per cell
    bob_grid = np.zeros((5, 5))
    comp_grid = np.zeros((5, 5))
    stop_grid = np.zeros((5, 5))

    for b in branches:
        if not (BAKU_CENTER['lat_min'] <= b['lat'] <= BAKU_CENTER['lat_max'] and
                BAKU_CENTER['lon_min'] <= b['lon'] <= BAKU_CENTER['lon_max']):
            continue
        lat_idx = min(int((b['lat'] - BAKU_CENTER['lat_min']) / (BAKU_CENTER['lat_max'] - BAKU_CENTER['lat_min']) * 5), 4)
        lon_idx = min(int((b['lon'] - BAKU_CENTER['lon_min']) / (BAKU_CENTER['lon_max'] - BAKU_CENTER['lon_min']) * 5), 4)
        if b['bank'] == BOB:
            bob_grid[lat_idx][lon_idx] += 1
        else:
            comp_grid[lat_idx][lon_idx] += 1

    for s in center_stops:
        lat_idx = min(int((s['lat'] - BAKU_CENTER['lat_min']) / (BAKU_CENTER['lat_max'] - BAKU_CENTER['lat_min']) * 5), 4)
        lon_idx = min(int((s['lon'] - BAKU_CENTER['lon_min']) / (BAKU_CENTER['lon_max'] - BAKU_CENTER['lon_min']) * 5), 4)
        stop_grid[lat_idx][lon_idx] += 1

    # Identify opportunity cells: high stops + competitors but no BOB
    opportunity_cells = []
    for i in range(5):
        for j in range(5):
            if bob_grid[i][j] == 0 and comp_grid[i][j] > 0 and stop_grid[i][j] > 20:
                lat_center = (lat_bins[i] + lat_bins[i + 1]) / 2
                lon_center = (lon_bins[j] + lon_bins[j + 1]) / 2
                opportunity_cells.append({
                    "lat": lat_center, "lon": lon_center,
                    "stops": stop_grid[i][j], "competitors": comp_grid[i][j]
                })

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    titles = ["Bus Stops Density", "Competitor Branches", "BOB Branches"]
    grids = [stop_grid, comp_grid, bob_grid]
    cmaps = ["Blues", "Oranges", "Greens"]

    for ax, title, grid, cmap in zip(axes, titles, grids, cmaps):
        im = ax.imshow(grid, cmap=cmap, aspect='auto', origin='lower')
        ax.set_title(title, fontsize=12, fontweight='bold', color="#2C3E50")
        ax.set_xlabel("Longitude zones (W → E)", fontsize=9)
        ax.set_ylabel("Latitude zones (S → N)", fontsize=9)
        # Add value labels
        for i in range(5):
            for j in range(5):
                val = int(grid[i][j])
                if val > 0:
                    ax.text(j, i, str(val), ha='center', va='center',
                            fontsize=10, fontweight='bold', color='white' if val > grid.max() * 0.5 else 'black')
        plt.colorbar(im, ax=ax, shrink=0.8)

    fig.suptitle("Baku Center Grid Analysis: Transit Density vs Branch Presence",
                 fontsize=14, fontweight='bold', color="#2C3E50")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "11_baku_center_density.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 11: Baku Center Density Grid")

    return opportunity_cells


def chart_12_bob_vs_kapital(accessibility):
    """Chart 12: Head-to-Head — BOB vs Kapital Bank Transit Accessibility"""
    bob = [a for a in accessibility if a['bank'] == BOB]
    kapital = [a for a in accessibility if a['bank'] == 'Kapital Bank']

    # Compare distributions
    bob_routes = sorted([a['nearby_routes'] for a in bob], reverse=True)
    kap_routes = sorted([a['nearby_routes'] for a in kapital], reverse=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # Histogram comparison
    max_val = max(max(bob_routes) if bob_routes else 0, max(kap_routes) if kap_routes else 0)
    bins = np.linspace(0, max_val, 15)

    ax1.hist(bob_routes, bins=bins, alpha=0.7, color=HIGHLIGHT_COLOR, label=f'BOB (n={len(bob)})', edgecolor='white')
    ax1.hist(kap_routes, bins=bins, alpha=0.5, color=ACCENT_COLOR, label=f'Kapital Bank (n={len(kapital)})', edgecolor='white')
    style_chart(ax1, "Distribution: Bus Routes Within Walking Distance",
                xlabel="Number of Bus Routes", ylabel="Number of Branches")
    ax1.legend(fontsize=10)

    # Summary stats comparison
    metrics = ['Avg Routes\nNearby', 'Avg Stops\nNearby', 'Median Nearest\nStop (m)']

    bob_stops_nearby = [a['nearby_stops'] for a in bob]
    kap_stops_nearby = [a['nearby_stops'] for a in kapital]
    bob_nearest = sorted([a['nearest_stop_m'] for a in bob])
    kap_nearest = sorted([a['nearest_stop_m'] for a in kapital])

    bob_vals = [
        sum(bob_routes) / len(bob_routes) if bob_routes else 0,
        sum(bob_stops_nearby) / len(bob_stops_nearby) if bob_stops_nearby else 0,
        bob_nearest[len(bob_nearest) // 2] if bob_nearest else 0
    ]
    kap_vals = [
        sum(kap_routes) / len(kap_routes) if kap_routes else 0,
        sum(kap_stops_nearby) / len(kap_stops_nearby) if kap_stops_nearby else 0,
        kap_nearest[len(kap_nearest) // 2] if kap_nearest else 0
    ]

    x = np.arange(len(metrics))
    width = 0.3
    ax2.bar(x - width / 2, bob_vals, width, label='BOB', color=HIGHLIGHT_COLOR, edgecolor='white')
    ax2.bar(x + width / 2, kap_vals, width, label='Kapital Bank', color=ACCENT_COLOR, edgecolor='white')

    for i in range(len(metrics)):
        ax2.text(x[i] - width / 2, bob_vals[i] + 0.5, f"{bob_vals[i]:.1f}",
                 ha='center', va='bottom', fontsize=9, fontweight='bold', color=HIGHLIGHT_COLOR)
        ax2.text(x[i] + width / 2, kap_vals[i] + 0.5, f"{kap_vals[i]:.1f}",
                 ha='center', va='bottom', fontsize=9, fontweight='bold', color=ACCENT_COLOR)

    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics, fontsize=10)
    style_chart(ax2, "Head-to-Head: BOB vs Kapital Bank", ylabel="Value")
    ax2.legend(fontsize=10)

    fig.suptitle("BOB vs Market Leader (Kapital Bank) — Transit Accessibility Comparison",
                 fontsize=14, fontweight='bold', color="#2C3E50", y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "12_bob_vs_kapital.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 12: BOB vs Kapital Bank")


def chart_13_accessibility_vs_size(accessibility, branch_counts):
    """Chart 13: Network Size vs Transit Accessibility — Scatter"""
    bank_data = {}
    for a in accessibility:
        bank = a['bank']
        if bank not in bank_data:
            bank_data[bank] = {'routes': [], 'stops': []}
        bank_data[bank]['routes'].append(a['nearby_routes'])
        bank_data[bank]['stops'].append(a['nearby_stops'])

    fig, ax = plt.subplots(figsize=(12, 8))

    for bank, data in bank_data.items():
        avg_routes = sum(data['routes']) / len(data['routes'])
        count = len(data['routes'])
        color = HIGHLIGHT_COLOR if bank == BOB else COMPETITOR_COLOR
        size = 200 if bank == BOB else 80
        alpha = 1.0 if bank == BOB else 0.6
        zorder = 10 if bank == BOB else 5

        ax.scatter(count, avg_routes, s=size, c=color, alpha=alpha,
                   edgecolors='white', linewidth=1, zorder=zorder)
        # Label significant banks
        if bank == BOB or count >= 30 or avg_routes >= 40:
            ax.annotate(bank, (count, avg_routes), fontsize=8, fontweight='bold',
                        xytext=(7, 7), textcoords='offset points',
                        color=HIGHLIGHT_COLOR if bank == BOB else '#555')

    style_chart(ax, "Network Size vs Average Transit Accessibility",
                xlabel="Number of Branches", ylabel=f"Avg Bus Routes Within {WALKING_DISTANCE}m")

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "13_size_vs_accessibility.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 13: Size vs Accessibility Scatter")


def chart_14_regional_presence(branches, branch_counts):
    """Chart 14: Regional Presence Comparison — Banks Present Outside Baku"""
    top_banks = [b[0] for b in branch_counts[:15]]

    regional = {}
    baku = {}
    for bank in top_banks:
        bank_branches = [b for b in branches if b['bank'] == bank]
        r = sum(1 for b in bank_branches if classify_location(b['lat'], b['lon']) == "Regional")
        bk = len(bank_branches) - r
        regional[bank] = r
        baku[bank] = bk

    sorted_banks = sorted(regional.items(), key=lambda x: -x[1])
    banks = [b[0] for b in sorted_banks]
    reg_vals = [regional[b] for b in banks]
    baku_vals = [baku[b] for b in banks]

    fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(banks))
    width = 0.35

    ax.bar(x - width / 2, baku_vals, width, label='Baku Area', color="#2E86C1", edgecolor='white')
    ax.bar(x + width / 2, reg_vals, width, label='Regional', color=SECONDARY_COLOR, edgecolor='white')

    for i in range(len(banks)):
        if baku_vals[i] > 0:
            ax.text(x[i] - width / 2, baku_vals[i] + 0.5, str(baku_vals[i]),
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
        if reg_vals[i] > 0:
            ax.text(x[i] + width / 2, reg_vals[i] + 0.5, str(reg_vals[i]),
                    ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(banks, fontsize=9)
    style_chart(ax, "Baku vs Regional Branch Distribution",
                ylabel="Number of Branches", rotate_x=35)
    ax.legend(fontsize=10)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "14_regional_presence.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 14: Regional Presence")


def chart_15_bob_competitive_landscape(overlap_data):
    """Chart 15: Which Competitors Are Closest to BOB Branches"""
    # Aggregate which banks appear most around BOB
    comp_totals = Counter()
    for o in overlap_data:
        for bank, count in o['competitor_banks'].items():
            comp_totals[bank] += count

    if not comp_totals:
        print("  Chart 15: Skipped (no competitor overlap)")
        return

    sorted_comps = comp_totals.most_common(15)
    banks = [c[0] for c in sorted_comps]
    counts = [c[1] for c in sorted_comps]

    fig, ax = plt.subplots(figsize=(12, 7))

    bars = ax.barh(range(len(banks)), counts, color=ACCENT_COLOR, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(banks)))
    ax.set_yticklabels(banks, fontsize=10)
    ax.invert_yaxis()

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(count), va='center', fontsize=10, fontweight='bold', color='#555')

    style_chart(ax, "Competitor Branches Within 500m of BOB Locations",
                xlabel="Number of Competitor Branches")
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.yaxis.grid(False)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "15_bob_competitive_landscape.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 15: BOB Competitive Landscape")


def chart_16_transit_gap_analysis(accessibility):
    """Chart 16: Branches with Poor Transit Access (< 3 stops within walking distance)"""
    poor_access = [a for a in accessibility if a['nearby_stops'] < 3]

    bank_poor = Counter(a['bank'] for a in poor_access)
    bank_total = Counter(a['bank'] for a in accessibility)

    # Calculate percentage with poor access
    bank_pct = {}
    for bank in bank_total:
        if bank_total[bank] >= 5:  # Only banks with 5+ branches
            bank_pct[bank] = (bank_poor.get(bank, 0) / bank_total[bank]) * 100

    sorted_banks = sorted(bank_pct.items(), key=lambda x: -x[1])
    banks = [b[0] for b in sorted_banks]
    pcts = [b[1] for b in sorted_banks]
    colors = [HIGHLIGHT_COLOR if b == BOB else COMPETITOR_COLOR for b in banks]

    fig, ax = plt.subplots(figsize=(14, 7))

    bars = ax.barh(range(len(banks)), pcts, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(banks)))
    ax.set_yticklabels(banks, fontsize=10)
    ax.invert_yaxis()

    for i, (bar, pct) in enumerate(zip(bars, pcts)):
        total = bank_total[banks[i]]
        poor = bank_poor.get(banks[i], 0)
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{pct:.0f}% ({poor}/{total})", va='center', fontsize=10, fontweight='bold',
                color=HIGHLIGHT_COLOR if banks[i] == BOB else '#555')

    style_chart(ax, "% of Branches with Poor Transit Access (< 3 Bus Stops Within 400m)",
                xlabel="% of Branches")
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.yaxis.grid(False)

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "16_transit_gap_analysis.png"), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("  Chart 16: Transit Gap Analysis")


# ──────────────────────────────────────────────
# Main Execution
# ──────────────────────────────────────────────
def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)

    # Load data
    branches, stops, buses, stop_route_count = load_data()

    # ── Core Analyses ──
    print("\nRunning analyses...")

    branch_counts = branches_by_bank(branches)
    print(f"  Banks: {len(branch_counts)}")

    bank_zones = zone_coverage_analysis(branches)
    print("  Zone coverage computed")

    print("  Computing accessibility (this may take a moment)...")
    accessibility = compute_accessibility(branches, stops)
    print(f"  Accessibility computed for {len(accessibility)} branches")

    print("  Computing hub proximity...")
    hub_data = compute_hub_proximity(branches, stops)
    print(f"  Hub proximity computed")

    print("  Finding expansion opportunities...")
    gaps = find_competitor_gaps(branches, stops)
    print(f"  Found {len(gaps)} gap opportunities")

    print("  Computing competitive overlap...")
    overlap_data = compute_competitive_overlap(branches)
    print(f"  Overlap computed for {len(overlap_data)} BOB branches")

    # ── Generate Charts ──
    print("\nGenerating charts...")

    chart_01_market_position(branch_counts)
    chart_02_geographic_distribution(bank_zones, branch_counts)
    chart_03_bob_vs_top5_geo(bank_zones, branch_counts)
    chart_04_transit_accessibility(accessibility, branch_counts)
    chart_05_route_connectivity(accessibility, branch_counts)
    chart_06_hub_proximity(hub_data, branch_counts)
    chart_07_bob_branch_scorecard(accessibility)
    chart_08_expansion_opportunities(gaps)
    chart_09_competitive_pressure(overlap_data)
    chart_10_nearest_stop_distribution(accessibility, branch_counts)
    opportunity_cells = chart_11_baku_center_density(branches, stops)
    chart_12_bob_vs_kapital(accessibility)
    chart_13_accessibility_vs_size(accessibility, branch_counts)
    chart_14_regional_presence(branches, branch_counts)
    chart_15_bob_competitive_landscape(overlap_data)
    chart_16_transit_gap_analysis(accessibility)

    # ── Print Summary Stats for README ──
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)

    bob_acc = [a for a in accessibility if a['bank'] == BOB]
    all_acc = accessibility

    print(f"\nTotal branches analyzed: {len(branches)}")
    print(f"Total banks: {len(branch_counts)}")
    print(f"Total bus stops: {len(stops)}")
    print(f"Total bus routes: {len(buses)}")

    print(f"\nBank of Baku:")
    print(f"  Branches: {len(bob_acc)}")
    bob_baku = [a for a in bob_acc
                if BAKU_GREATER['lat_min'] <= a['lat'] <= BAKU_GREATER['lat_max']]
    bob_regional = [a for a in bob_acc
                    if not (BAKU_GREATER['lat_min'] <= a['lat'] <= BAKU_GREATER['lat_max'])]
    print(f"  Baku area: {len(bob_baku)}, Regional: {len(bob_regional)}")
    print(f"  Avg stops within {WALKING_DISTANCE}m: {sum(a['nearby_stops'] for a in bob_acc) / len(bob_acc):.1f}")
    print(f"  Avg routes within {WALKING_DISTANCE}m: {sum(a['nearby_routes'] for a in bob_acc) / len(bob_acc):.1f}")

    print(f"\nMarket Leader (Kapital Bank):")
    kap_acc = [a for a in accessibility if a['bank'] == 'Kapital Bank']
    print(f"  Branches: {len(kap_acc)}")
    print(f"  Avg stops within {WALKING_DISTANCE}m: {sum(a['nearby_stops'] for a in kap_acc) / len(kap_acc):.1f}")
    print(f"  Avg routes within {WALKING_DISTANCE}m: {sum(a['nearby_routes'] for a in kap_acc) / len(kap_acc):.1f}")

    print(f"\nExpansion opportunities (high-traffic, no BOB): {len(gaps)}")
    if opportunity_cells:
        print(f"Grid cells in Baku center with transit but no BOB: {len(opportunity_cells)}")

    print(f"\nAll 16 charts saved to {CHARTS_DIR}/")
    print("Done!")


if __name__ == "__main__":
    main()
