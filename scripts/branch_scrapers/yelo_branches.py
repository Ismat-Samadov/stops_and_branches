#!/usr/bin/env python3
"""
Yelo Bank Azerbaijan Branch Scraper
Fetches branch data from Yelo Bank's website and saves to CSV.
"""

import requests
from bs4 import BeautifulSoup
import csv
import re
from typing import List, Dict


class YeloBankScraper:
    """Scraper for Yelo Bank branch locations."""

    PAGE_URL = "https://www.yelo.az/az/individuals/atms-and-branches/"
    OUTPUT_FILE = "data/yelo_branches.csv"

    def __init__(self):
        self.branches = []

    def fetch_page(self) -> str:
        """Fetch the HTML page containing branch data."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(self.PAGE_URL, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text

    def clean_text(self, text: str) -> str:
        """Clean extra whitespace from text."""
        if not text:
            return ""
        text = ' '.join(text.split())
        return text.strip()

    def extract_branches(self, html_content: str) -> List[Dict]:
        """Extract branch data from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        branches = []

        # Find all branch items - filter by data-filter="pin1176" (branches, not ATMs which are pin1177)
        branch_items = soup.find_all('a', class_='b_item', attrs={'data-filter': 'pin1176'})

        print(f"Found {len(branch_items)} branches in HTML")

        for item in branch_items:
            # Extract name from <b> tag
            name_elem = item.find('b')
            name = ''
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            # Skip ATMs
            if 'ATM' in name or 'atm' in name.lower():
                continue

            # Extract metro station
            metro_elem = item.find('span', class_='metro')
            metro = ''
            if metro_elem:
                metro = self.clean_text(metro_elem.get_text())

            # Extract address
            address_elem = item.find('li', class_='pin_call')
            address = ''
            if address_elem:
                address = self.clean_text(address_elem.get_text())

            # Extract working hours
            time_elem = item.find('li', class_='pin_time')
            working_hours = ''
            if time_elem:
                # Get text, but skip the tooltip div
                for tooltip in time_elem.find_all('div', class_='info_container'):
                    tooltip.decompose()
                working_hours = self.clean_text(time_elem.get_text())

            # Extract data-id
            data_id = item.get('data-id', '')

            # Extract coordinates from Google Maps link
            latitude = ''
            longitude = ''

            # Find the next sibling span with class "map_link show_me"
            map_link = item.find_next_sibling('span', class_='map_link show_me')
            if map_link:
                google_link = map_link.find('a')
                if google_link:
                    href = google_link.get('href', '')
                    # Extract coordinates from URL: destination=40.403065,49.806690
                    coord_match = re.search(r'destination=([\d.]+),([\d.]+)', href)
                    if coord_match:
                        latitude = coord_match.group(1)
                        longitude = coord_match.group(2)

            branch = {
                'id': data_id,
                'name': name,
                'metro': metro,
                'address': address,
                'latitude': latitude,
                'longitude': longitude,
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
            'id', 'name', 'metro', 'address', 'latitude', 'longitude', 'working_hours'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Yelo Bank branches page...")
        html = self.fetch_page()

        print("Extracting branch data from page...")
        self.branches = self.extract_branches(html)

        print(f"\nExtracted {len(self.branches)} branches (ATMs excluded)")

        # Count how many have coordinates
        with_coords = sum(1 for b in self.branches if b['latitude'] and b['longitude'])
        print(f"Branches with coordinates: {with_coords}/{len(self.branches)}")

        print("\nSaving to CSV...")
        self.save_to_csv(self.branches)

        # Print first branch as example
        if self.branches:
            print("\nExample (first branch):")
            import json
            print(json.dumps(self.branches[0], ensure_ascii=False, indent=2))

        print("Done!")


def main():
    scraper = YeloBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
