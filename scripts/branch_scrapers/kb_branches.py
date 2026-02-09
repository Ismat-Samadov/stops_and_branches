#!/usr/bin/env python3
"""
Kapital Bank Branch Scraper
Fetches branch data from Kapital Bank's website and saves to CSV.
"""

import aiohttp
import asyncio
import csv
import re
import json
from typing import List, Dict


class KapitalBankScraper:
    """Scraper for Kapital Bank branch locations."""

    PAGE_URL = "https://www.kapitalbank.az/locations/branch/all"
    OUTPUT_FILE = "data/kb_branches.csv"

    def __init__(self):
        self.branches = []

    async def fetch_page(self) -> str:
        """Fetch the HTML page containing branch data."""
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
            }
            async with session.get(self.PAGE_URL, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"Failed to fetch page: HTTP {response.status}")

    def extract_branches(self, html: str) -> List[Dict]:
        """Extract branch data from embedded JavaScript in HTML."""
        branches = []

        # Look for window.filter_branches = [...]
        pattern = r'window\.filter_branches\s*=\s*(\[[\s\S]*?\]);'
        match = re.search(pattern, html)

        if not match:
            print("Could not find window.filter_branches in page")
            return branches

        json_str = match.group(1)

        try:
            branches_data = json.loads(json_str)
            print(f"Found {len(branches_data)} branches in JavaScript data")

            for branch in branches_data:
                # Use the summary working hours fields
                work_week = branch.get('work_hours_week', '')
                work_sat = branch.get('work_hours_saturday', '')
                work_sun = branch.get('work_hours_sunday', '')

                working_hours = f"Mon-Fri: {work_week}; Sat: {work_sat}; Sun: {work_sun}"

                branches.append({
                    'id': branch.get('id', ''),
                    'name': branch.get('name', ''),
                    'city_name': branch.get('city_name', ''),
                    'address': branch.get('address', ''),
                    'city_id': branch.get('city_id', ''),
                    'slug': branch.get('slug', ''),
                    'latitude': branch.get('lat', ''),
                    'longitude': branch.get('lng', ''),
                    'is_open': branch.get('is_open', ''),
                    'usd': branch.get('usd', ''),
                    'cash_in': branch.get('cash_in', ''),
                    'is_nfc': branch.get('is_nfc', ''),
                    'is_digital': branch.get('is_digital', ''),
                    'payment_terminal': branch.get('payment_terminal', ''),
                    'working_weekends': branch.get('working_weekends', ''),
                    'working_hours': working_hours,
                    'notes': branch.get('notes', '') or '',
                })

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            # Try to save the problematic JSON for debugging
            with open('/tmp/kb_branches_debug.json', 'w') as f:
                f.write(json_str)
            print("Saved problematic JSON to /tmp/kb_branches_debug.json")

        return branches

    def format_working_hours(self, working_days: List[Dict]) -> str:
        """Format working hours from array to readable string."""
        if not working_days:
            return ""

        # Group consecutive days with same hours
        hours_str = []
        for day in working_days:
            day_name = day.get('name', '')
            start = day.get('start', '')
            end = day.get('end', '')

            if start and end:
                hours_str.append(f"{day_name}: {start}-{end}")
            elif day_name:
                hours_str.append(f"{day_name}: Closed")

        return "; ".join(hours_str)

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'id', 'name', 'city_name', 'address', 'city_id', 'slug',
            'latitude', 'longitude',
            'is_open', 'usd', 'cash_in', 'is_nfc', 'is_digital',
            'payment_terminal', 'working_weekends',
            'working_hours', 'notes'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    async def run(self):
        """Main execution method."""
        print("Fetching Kapital Bank locations page...")
        html = await self.fetch_page()

        print("Extracting branch data from page...")
        self.branches = self.extract_branches(html)

        print(f"\nFound {len(self.branches)} branches")

        # Count how many have coordinates
        with_coords = sum(1 for b in self.branches if b['latitude'] and b['longitude'])
        print(f"Branches with coordinates: {with_coords}/{len(self.branches)}")

        print("\nSaving to CSV...")
        self.save_to_csv(self.branches)

        print("Done!")


async def main():
    scraper = KapitalBankScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
