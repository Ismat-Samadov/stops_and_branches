#!/usr/bin/env python3
"""
Combine Supermarket Data
Merges all supermarket chain data into a single dataset for analysis
"""

import csv
import os
from typing import List, Dict


def combine_supermarket_data(
    input_files: List[str],
    output_file: str = 'data/combined.csv'
) -> None:
    """
    Combine multiple supermarket CSV files into one dataset

    Args:
        input_files: List of CSV file paths to combine
        output_file: Path to output combined CSV file
    """
    combined_data = []

    print("=" * 60)
    print("Combining Supermarket Chain Data")
    print("=" * 60)

    for file_path in input_files:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found, skipping...")
            continue

        # Extract chain name from filename
        chain_name = os.path.basename(file_path).replace('.csv', '').upper()

        print(f"\nReading {chain_name} data from {file_path}...")

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0

            for row in reader:
                # Add chain identifier to each row
                row['chain'] = chain_name
                combined_data.append(row)
                count += 1

            print(f"  Added {count} stores from {chain_name}")

    # Write combined data
    if combined_data:
        # Collect all unique fieldnames from all rows
        all_fields = set()
        for row in combined_data:
            all_fields.update(row.keys())

        # Order fieldnames: chain first, then common fields, then extras
        common_fields = ['chain', 'name', 'address', 'phone', 'hours', 'latitude', 'longitude']
        extra_fields = sorted(all_fields - set(common_fields))
        fieldnames = common_fields + extra_fields

        print(f"\nWriting combined data to {output_file}...")

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(combined_data)

        print(f"Successfully combined {len(combined_data)} stores into {output_file}")

        # Print summary by chain
        print("\n" + "=" * 60)
        print("Summary by Chain:")
        print("=" * 60)

        chain_counts = {}
        for row in combined_data:
            chain = row['chain']
            chain_counts[chain] = chain_counts.get(chain, 0) + 1

        for chain, count in sorted(chain_counts.items()):
            print(f"  {chain}: {count} stores")

        print(f"\n  TOTAL: {len(combined_data)} stores")
        print("=" * 60)
    else:
        print("\nNo data to combine")


def main():
    """Main execution function"""
    input_files = [
        'data/bravo.csv',
        'data/araz.csv',
        'data/rahat.csv',
        'data/oba.csv',
        'data/tam.csv'
    ]

    combine_supermarket_data(input_files)


if __name__ == "__main__":
    main()
