#!/usr/bin/env python3
"""
AtaBank (ATB) Azerbaijan Branch Scraper
Fetches branch data from ATB's website and saves to CSV.
"""

import os
import requests
from bs4 import BeautifulSoup
import csv
import re
import json
from typing import List, Dict, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class ATBScraper:
    """Scraper for AtaBank branch locations."""

    PAGE_URL = "https://atb.az/filial/"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "atb_branches.csv")

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

    def extract_coordinates(self, html_content: str) -> Dict[str, Tuple[float, float]]:
        """Extract coordinate data from JavaScript mapData variable."""
        coords_map = {}

        # Find the mapData JavaScript variable with JSON.parse
        match = re.search(r'const\s+mapData\s*=\s*JSON\.parse\(\s*\'(.*?)\'\s*\);', html_content, re.DOTALL)
        if not match:
            print("Warning: Could not find mapData")
            return coords_map

        try:
            # Get the JSON string (it's escaped in the JavaScript)
            map_data_json = match.group(1)
            # Unescape the JSON string
            map_data_json = map_data_json.replace(r'\"', '"')

            # Parse the JSON array
            features = json.loads(map_data_json)

            # Extract coordinate data from each feature
            for feature in features:
                if not isinstance(feature, dict):
                    continue

                properties = feature.get('properties', {})
                marker_id = properties.get('markerId')  # markerId, not id!

                # Get coordinates from properties
                coords = properties.get('coordinates', {})
                lng = coords.get('x')  # longitude
                lat = coords.get('y')  # latitude

                if marker_id and lat and lng:
                    # Store with marker ID as key
                    coords_map[str(marker_id)] = (lat, lng)

            print(f"Extracted coordinates for {len(coords_map)} locations from JavaScript mapData")
        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            print(f"Warning: Could not parse mapData: {e}")

        return coords_map

    def is_branch(self, name: str) -> bool:
        """Check if the location is a branch (not ATM or terminal)."""
        name_lower = name.lower()

        # Exclude ATMs and terminals
        if 'atm' in name_lower or 'bankomat' in name_lower:
            return False
        if 'terminal' in name_lower:
            return False

        # Must contain "filial" or specific branch keywords
        if 'filial' in name_lower:
            return True
        if 'mərkəz' in name_lower and 'xidmət' in name_lower:  # Service center
            return True
        if 'ofis' in name_lower:  # Office
            return True

        return False

    def extract_branches(self, html_content: str, coords_map: Dict[str, Tuple[float, float]]) -> List[Dict]:
        """Extract branch data from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        branches = []

        # Find all branch items
        branch_items = soup.find_all('li', class_='map-content__item')

        print(f"Found {len(branch_items)} locations in HTML")

        for item in branch_items:
            # Extract marker ID (used to match with coordinates)
            marker_id = item.get('data-current-marker', '')

            # Extract branch name
            name_elem = item.find('div', class_='map-content__title')
            name = ''
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            # Skip if no name
            if not name:
                continue

            # Only keep branches, skip ATMs and terminals
            if not self.is_branch(name):
                continue

            # Extract working hours from map-content__text div
            hours_elem = item.find('div', class_='map-content__text')
            working_hours = ''
            if hours_elem:
                # Get first div within map-content__text (contains hours)
                first_div = hours_elem.find('div')
                if first_div:
                    working_hours = self.clean_text(first_div.get_text())

            # Extract address
            address_elem = item.find('div', class_='map-content__address')
            address = ''
            if address_elem:
                address_text = address_elem.get_text()
                # Remove "ünvan:" prefix
                address = self.clean_text(address_text.replace('ünvan:', '').strip())

            # Get coordinates from the coords_map using marker ID
            latitude = ''
            longitude = ''
            if marker_id and marker_id in coords_map:
                lat, lng = coords_map[marker_id]
                latitude = str(lat)
                longitude = str(lng)

            branch = {
                'marker_id': marker_id,
                'name': name,
                'address': address,
                'latitude': latitude,
                'longitude': longitude,
                'working_hours': working_hours
            }

            branches.append(branch)

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'marker_id', 'name', 'address', 'latitude', 'longitude', 'working_hours'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching AtaBank branches page...")
        html = self.fetch_page()

        print("Extracting coordinates from JavaScript mapData...")
        coords_map = self.extract_coordinates(html)

        print("Extracting branch data from page...")
        self.branches = self.extract_branches(html, coords_map)

        print(f"\nExtracted {len(self.branches)} branches (ATMs and terminals excluded)")

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
    scraper = ATBScraper()
    scraper.run()


if __name__ == "__main__":
    main()
