#!/usr/bin/env python3
"""
VTB Bank Azerbaijan Branch Scraper
Fetches branch data from VTB's website and saves to CSV.
"""

import os
import requests
from bs4 import BeautifulSoup
import csv
import re
from typing import List, Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class VTBScraper:
    """Scraper for VTB Bank branch locations."""

    PAGE_URL = "https://vtb.az/offices/?tab=branches"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "vtb_branches.csv")

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

        # Clean up whitespace
        text = ' '.join(text.split())

        return text.strip()

    def extract_branches(self, html_content: str) -> List[Dict]:
        """Extract branch data from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        branches = []

        # Find all office list items
        office_items = soup.find_all('li', class_='offices__list__item')

        print(f"Found {len(office_items)} locations in HTML (branches + ATMs)")

        for item in office_items:
            # Extract coordinates from data attributes
            latitude = item.get('data-lat', '').strip()
            longitude = item.get('data-long', '').strip()

            # Extract title
            title_elem = item.find('h2', class_='offices__list__item__title')
            title = ''
            if title_elem:
                title = self.clean_text(title_elem.get_text())

            # Skip if no title
            if not title:
                continue

            # Only include actual branches (not ATMs)
            # Branches contain "Filial" or "Baş ofis" in their name
            if 'Filial' not in title and 'Baş ofis' not in title:
                continue

            # Extract address and working hours from contacts list
            contacts_list = item.find('ul', class_='offices__list__item__contacts')
            address = ''
            working_hours = ''

            if contacts_list:
                contact_items = contacts_list.find_all('li')
                for contact_item in contact_items:
                    contact_text = self.clean_text(contact_item.get_text())

                    # Try to separate address and working hours
                    # Pattern: address, then "İş qrafiki:" or "İş vaxtı:"
                    if 'İş qrafiki:' in contact_text or 'İş vaxtı:' in contact_text:
                        # Split by working hours indicator
                        parts = re.split(r'[.,]\s*İş\s+(?:qrafiki|vaxtı):', contact_text)
                        if len(parts) >= 2:
                            address = parts[0].strip()
                            working_hours = f"İş qrafiki: {parts[1].strip()}"
                        else:
                            address = contact_text
                    else:
                        address = contact_text

            branch = {
                'name': title,
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

        # Deduplicate by name
        unique_branches = {}
        for branch in branches:
            name = branch['name']
            if name not in unique_branches:
                unique_branches[name] = branch

        branches_list = list(unique_branches.values())

        fieldnames = [
            'name', 'address', 'latitude', 'longitude', 'working_hours'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches_list)

        print(f"Saved {len(branches_list)} unique branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching VTB Bank branches page...")
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
    scraper = VTBScraper()
    scraper.run()


if __name__ == "__main__":
    main()
