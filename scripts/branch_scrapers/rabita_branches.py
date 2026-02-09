#!/usr/bin/env python3
"""
Rabita Bank Azerbaijan Branch Scraper
Fetches branch data from Rabita Bank's API and saves to CSV.
"""

import os
import requests
import csv
import json
from typing import List, Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class RabitaBankScraper:
    """Scraper for Rabita Bank branch locations."""

    API_URL = "https://www.rabitabank.com/filial-ve-bankomatlar/filiallar?q="
    BASE_URL = "https://www.rabitabank.com"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "rabita_branches.csv")

    def __init__(self):
        self.branches = []
        self.session = requests.Session()

    def fetch_data(self) -> dict:
        """Fetch data from Rabita Bank API."""

        # First, visit the main page to get cookies and CSRF token
        main_page_response = self.session.get(f"{self.BASE_URL}/filial-ve-bankomatlar/filiallar")

        # Extract XSRF token from cookies
        xsrf_token = self.session.cookies.get('XSRF-TOKEN', '')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': f'{self.BASE_URL}/filial-ve-bankomatlar/filiallar',
            'X-Requested-With': 'XMLHttpRequest',
            'X-XSRF-TOKEN': xsrf_token
        }

        response = self.session.get(self.API_URL, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8'

        print(f"Response status: {response.status_code}")
        print(f"Response content type: {response.headers.get('content-type')}")

        return response.json()

    def extract_branches(self, data: dict) -> List[Dict]:
        """Extract branch data from API response."""
        branches = []

        print(f"API response type: {type(data)}")

        # Save full response for debugging
        with open('/tmp/rabita_response.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Full response saved to /tmp/rabita_response.json")

        # The response might be a list or a dict
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common patterns
            items = data.get('data', data.get('branches', data.get('items', [])))
            if isinstance(items, dict):
                # If items is still a dict, look for lists inside
                for key in items.keys():
                    if isinstance(items[key], list):
                        items = items[key]
                        break
        else:
            print(f"Unexpected data type: {type(data)}")
            return branches

        if not isinstance(items, list):
            print(f"Warning: Expected list but got {type(items)}")
            # Save response for debugging
            with open('/tmp/rabita_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("Response saved to /tmp/rabita_response.json")
            return branches

        print(f"Found {len(items)} total locations in API response")

        for item in items:
            # Determine if this is a branch or ATM
            item_type = item.get('type', '').lower()
            title = item.get('title', '')

            # Skip ATMs - only include branches (network_branch type)
            if 'atm' in item_type or 'bankomat' in item_type:
                continue
            if 'atm' in title.lower() or 'bankomat' in title.lower():
                continue

            # Extract coordinates from nested object
            coordinates = item.get('coordinates', {})
            latitude = coordinates.get('latitude', '')
            longitude = coordinates.get('longitude', '')

            # Combine working hours
            work_hours = item.get('work_hours', '')
            work_hours_weekend = item.get('work_hours_weekend', '')
            working_hours = work_hours
            if work_hours_weekend:
                working_hours += f" | Həftəsonu: {work_hours_weekend}"

            # Extract details
            branch = {
                'id': item.get('id', ''),
                'name': title,
                'short_address': item.get('short_address', ''),
                'address': item.get('address', ''),
                'latitude': latitude,
                'longitude': longitude,
                'working_hours': working_hours,
                'type': item.get('type', ''),
            }

            branches.append(branch)

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'id', 'name', 'short_address', 'address', 'latitude', 'longitude',
            'working_hours', 'type'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Rabita Bank data from API...")
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
    scraper = RabitaBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
