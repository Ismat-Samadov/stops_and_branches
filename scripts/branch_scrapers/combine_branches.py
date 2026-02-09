#!/usr/bin/env python3
"""
Combine all bank branch CSV files into a single file.
Output: data/branches/combined_branches.csv with columns: bank_name, lat, long
"""

import csv
import os
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class BranchCombiner:
    """Combines all bank branch CSV files into one unified file."""

    DATA_DIR = os.path.join(ROOT_DIR, "data", "branches")
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "combined_branches.csv")

    # Mapping of CSV files to bank names
    BANK_FILES = {
        'ab_branches.csv': 'AccessBank',
        'abb_branches.csv': 'ABB Bank',
        'asb_branches.csv': 'ASB Bank',
        'bob_branches.csv': 'Bank of Baku',
        'br_branches.csv': 'Bank Respublika',
        'kb_branches.csv': 'Kapital Bank',
        'premium_branches.csv': 'Premium Bank',
        'rabita_branches.csv': 'Rabita Bank',
        'vtb_branches.csv': 'VTB Bank',
        'xalq_branches.csv': 'Xalq Bank',
        'yelo_branches.csv': 'Yelo Bank',
        'ub_branches.csv': 'Unibank',
        'atb_branches.csv': 'AzerTurk Bank',
        'afb_branches.csv': 'AFB',
        'expressbank_branches.csv': 'Express Bank',
        'turanbank_branches.csv': 'Turan Bank',
        'yapikredi_branches.csv': 'Yapi Kredi Bank',
        'ziraatbank_branches.csv': 'Ziraat Bank',
        'pashabank_branches.csv': 'Pasha Bank',
        'btb_branches.csv': 'BTB',
    }

    def __init__(self):
        self.combined_branches = []

    def read_csv_file(self, filepath: str, bank_name: str):
        """Read a CSV file and extract bank_name, lat, long."""
        branches = []

        try:
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    # Get latitude and longitude (try both common column names)
                    lat = row.get('latitude', row.get('lat', ''))
                    long = row.get('longitude', row.get('long', row.get('lon', '')))

                    # Only include branches with valid coordinates
                    if lat and long:
                        try:
                            # Validate that they're numeric
                            float(lat)
                            float(long)

                            branches.append({
                                'bank_name': bank_name,
                                'lat': lat,
                                'long': long
                            })
                        except ValueError:
                            # Skip invalid coordinates
                            continue

            return branches
        except FileNotFoundError:
            print(f"Warning: File not found: {filepath}")
            return []
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return []

    def combine_all(self):
        """Read and combine all bank CSV files."""
        for filename, bank_name in self.BANK_FILES.items():
            filepath = os.path.join(self.DATA_DIR, filename)
            print(f"Reading {bank_name} from {filename}...")

            branches = self.read_csv_file(filepath, bank_name)
            self.combined_branches.extend(branches)

            print(f"  Found {len(branches)} branches with coordinates")

        return self.combined_branches

    def save_combined(self):
        """Save combined data to CSV."""
        if not self.combined_branches:
            print("No branches to save.")
            return

        fieldnames = ['bank_name', 'lat', 'long']

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.combined_branches)

        print(f"\nSaved {len(self.combined_branches)} total branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("=" * 60)
        print("Combining all bank branch CSV files")
        print("=" * 60)
        print()

        self.combine_all()

        print()
        print("=" * 60)
        print(f"Total branches collected: {len(self.combined_branches)}")
        print("=" * 60)
        print()

        # Show breakdown by bank
        bank_counts = {}
        for branch in self.combined_branches:
            bank = branch['bank_name']
            bank_counts[bank] = bank_counts.get(bank, 0) + 1

        print("Breakdown by bank:")
        for bank, count in sorted(bank_counts.items()):
            print(f"  {bank:20s}: {count:3d} branches")

        print()
        self.save_combined()

        # Show first few entries as example
        if self.combined_branches:
            print("\nExample entries (first 3):")
            for i, branch in enumerate(self.combined_branches[:3], 1):
                print(f"  {i}. {branch['bank_name']:20s} - ({branch['lat']}, {branch['long']})")

        print("\nDone!")


def main():
    combiner = BranchCombiner()
    combiner.run()


if __name__ == "__main__":
    main()
