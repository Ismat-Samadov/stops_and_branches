#!/usr/bin/env python3
"""
Express Bank Azerbaijan Branch Scraper
Fetches branch data from Express Bank's website and saves to CSV.
"""

import requests
import csv
import re
import json
from typing import List, Dict


class ExpressBankScraper:
    """Scraper for Express Bank branch locations."""

    PAGE_URL = "https://www.expressbank.az/az/page/xidmet-sebekesi"
    OUTPUT_FILE = "data/expressbank_branches.csv"

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
        """Extract branch data from JavaScript window.filials variable."""
        branches = []

        # Find the window.filials JavaScript variable
        match = re.search(r'window\.filials\s*=\s*(\[.*?\]);', html_content, re.DOTALL)
        if not match:
            print("Warning: Could not find window.filials data")
            return branches

        try:
            filials_json = match.group(1)
            filials_data = json.loads(filials_json)

            print(f"Found {len(filials_data)} branches in JavaScript data")

            for branch in filials_data:
                if not isinstance(branch, dict):
                    continue

                # Get the current language data (az)
                branch_id = branch.get('id')
                title = branch.get('title', '')
                addr = branch.get('addr', '')
                telephone = branch.get('telephone_number', '')
                working_hours = branch.get('working_hours', '')
                mail = ''

                # Get languages array to find the mail
                languages = branch.get('languages', [])
                if languages and len(languages) > 0:
                    # Get first language entry (az)
                    first_lang = languages[0]
                    if isinstance(first_lang, dict):
                        mail = first_lang.get('mail', '')

                # Get coordinates
                latitude = ''
                longitude = ''
                coordinate = branch.get('coordinate')
                if coordinate and isinstance(coordinate, dict):
                    lat = coordinate.get('lat')
                    lng = coordinate.get('long')
                    if lat and lng:
                        latitude = str(lat)
                        longitude = str(lng)

                # Filter: only category_id = 1 (branches, not ATMs)
                category_id = branch.get('category_id')
                if category_id != 1:
                    continue

                branch_data = {
                    'id': branch_id,
                    'name': self.clean_text(title),
                    'address': self.clean_text(addr),
                    'phone': self.clean_text(telephone),
                    'email': mail,
                    'working_hours': self.clean_text(working_hours),
                    'latitude': latitude,
                    'longitude': longitude
                }

                branches.append(branch_data)

            print(f"Filtered to {len(branches)} branches (category_id=1)")

        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Warning: Could not parse window.filials data: {e}")

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'id', 'name', 'address', 'phone', 'email', 'working_hours', 'latitude', 'longitude'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Express Bank branches page...")
        html = self.fetch_page()

        print("Extracting branch data from JavaScript...")
        self.branches = self.extract_branches(html)

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
    scraper = ExpressBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
