#!/usr/bin/env python3
"""
Xalq Bank Azerbaijan Branch Scraper
Fetches branch data from Xalq Bank's API and saves to CSV.
"""

import requests
import csv
import json
from typing import List, Dict


class XalqBankScraper:
    """Scraper for Xalq Bank branch locations."""

    API_URL = "https://xalqbank.az/api/az/xidmet-sebekesi?include=menu"
    BASE_URL = "https://xalqbank.az"
    OUTPUT_FILE = "data/xalq_branches.csv"

    def __init__(self):
        self.branches = []
        self.session = requests.Session()

    def fetch_data(self) -> dict:
        """Fetch data from Xalq Bank API."""

        # First, visit the main page to get cookies
        self.session.get(f"{self.BASE_URL}/az/xidmet-sebekesi")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': f'{self.BASE_URL}/az/xidmet-sebekesi',
            'X-Requested-With': 'XMLHttpRequest'
        }

        response = self.session.get(self.API_URL, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8'

        print(f"Response status: {response.status_code}")
        print(f"Response content type: {response.headers.get('content-type')}")

        if 'application/json' not in response.headers.get('content-type', ''):
            print(f"Warning: Expected JSON but got: {response.headers.get('content-type')}")
            print(f"Response text (first 500 chars): {response.text[:500]}")
            raise Exception("API did not return JSON")

        return response.json()

    def extract_branches(self, data: dict) -> List[Dict]:
        """Extract branch data from API response."""
        branches = []

        # Extract blocks from the response
        page_data = data.get('data', {})
        blocks = page_data.get('blocks', [])

        if not blocks:
            print("No blocks found in response")
            return branches

        # The first block contains the branches/ATMs
        main_block = blocks[0]
        items = main_block.get('blocks', [])

        print(f"Found {len(items)} total locations in API response")

        for item in items:
            # Check category to filter branches only
            category = item.get('category', {})
            category_name = category.get('category_name', '')

            # Skip ATMs and Cash In machines - only include branches (Filiallar)
            if 'ATM' in category_name or 'atm' in category_name.lower():
                continue
            if 'Cash In' in category_name or 'cash in' in category_name.lower():
                continue

            # Also check the title
            title = item.get('title', '').lower()
            if 'atm' in title or 'cash' in title:
                continue

            # Extract working hours
            working_days = item.get('working_days', [])
            working_hours = ''
            if working_days:
                hours_parts = []
                for day in working_days:
                    title = day.get('title', '')
                    value = day.get('value', '')
                    if title and value:
                        hours_parts.append(f"{title}: {value}")
                working_hours = ' | '.join(hours_parts)

            # Extract coordinates
            coordinates = item.get('coordinates', {})
            latitude = coordinates.get('latitude', '')
            longitude = coordinates.get('longitude', '')

            branch = {
                'id': item.get('id', ''),
                'name': item.get('title', ''),
                'slug': item.get('slug', ''),
                'category': category_name,
                'address': item.get('address', ''),
                'latitude': latitude,
                'longitude': longitude,
                'phone': item.get('phone', ''),
                'director': item.get('director', ''),
                'working_hours': working_hours,
            }

            branches.append(branch)

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'id', 'name', 'slug', 'category', 'address',
            'latitude', 'longitude', 'phone', 'director', 'working_hours'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Xalq Bank data from API...")
        data = self.fetch_data()

        print("\nExtracting branch data from API response...")
        self.branches = self.extract_branches(data)

        print(f"\nExtracted {len(self.branches)} branches")

        # Count how many have coordinates
        with_coords = sum(1 for b in self.branches if b['latitude'] and b['longitude'])
        print(f"Branches with coordinates: {with_coords}/{len(self.branches)}")

        print("\nSaving to CSV...")
        self.save_to_csv(self.branches)

        # Print first branch as example
        if self.branches:
            print("\nExample (first branch):")
            print(json.dumps(self.branches[0], ensure_ascii=False, indent=2))

        print("Done!")


def main():
    scraper = XalqBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
