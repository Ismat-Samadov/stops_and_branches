#!/usr/bin/env python3
"""
Unibank Azerbaijan Branch Scraper
Fetches branch data from Unibank's website and saves to CSV.
"""

import os
import requests
from bs4 import BeautifulSoup
import csv
import re
import json
from typing import List, Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class UnibankScraper:
    """Scraper for Unibank branch locations."""

    PAGE_URL = "https://unibank.az/locations/index"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "ub_branches.csv")

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

    def normalize_name(self, name: str) -> str:
        """Normalize branch name for deduplication."""
        # Remove quotes, extra spaces, normalize endings
        normalized = name.replace('"', '').replace('  ', ' ').strip().lower()
        # Normalize filial/filialı endings
        normalized = normalized.replace('filialı', 'filial')
        # Remove content in parentheses and extra spaces for more aggressive matching
        normalized = re.sub(r'\s*\([^)]*\)', '', normalized).strip()
        # Normalize multiple spaces
        normalized = ' '.join(normalized.split())
        return normalized

    def extract_coordinates(self, html_content: str) -> Dict[str, tuple]:
        """Extract coordinate data from JavaScript serviceNodes array."""
        coords_map = {}

        # Find the serviceNodes JavaScript array
        match = re.search(r'serviceNodes\s*=\s*(\[.*?\]);', html_content, re.DOTALL)
        if not match:
            print("Warning: Could not find serviceNodes data")
            return coords_map

        try:
            service_nodes_text = match.group(1)
            service_nodes = json.loads(service_nodes_text)

            # serviceNodes is a nested array: [[branches], [atms]]
            # Flatten the nested structure
            for group in service_nodes:
                if isinstance(group, list):
                    for node in group:
                        if isinstance(node, dict):
                            node_id = str(node.get('id', ''))
                            lat = node.get('lat')
                            lng = node.get('lng')

                            if node_id and lat and lng:
                                coords_map[node_id] = (lat, lng)

            print(f"Extracted coordinates for {len(coords_map)} locations from JavaScript data")
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Warning: Could not parse serviceNodes data: {e}")

        return coords_map

    def extract_branches(self, html_content: str, coords_map: Dict[str, tuple]) -> List[Dict]:
        """Extract branch data from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        branches = []
        seen_ids = set()  # Track IDs to avoid duplicates
        seen_names = set()  # Track normalized names to avoid duplicates

        # Find all branch items with class "js--loc"
        branch_items = soup.find_all('div', class_='js--loc')

        print(f"Found {len(branch_items)} locations in HTML")

        for item in branch_items:
            # Extract data-id
            data_id = item.get('data-id', '')

            # Skip if we've already seen this ID
            if data_id and data_id in seen_ids:
                continue

            # Extract name from p.text--bold
            name_elem = item.find('p', class_='text--bold')
            name = ''
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            # Skip if no name (might be ATM or invalid entry)
            if not name:
                continue

            # Skip ATMs
            if 'ATM' in name or 'atm' in name.lower() or 'bankomat' in name.lower():
                continue

            # Skip non-branch entities (central office, business centers, etc.)
            # Only keep branches with "filial" in the name
            name_lower = name.lower()
            if 'mərkəzi ofis' in name_lower or 'biznes mərkəzi' in name_lower:
                continue

            # Must contain "filial" to be considered a branch
            if 'filial' not in name_lower:
                continue

            # Check for duplicate names (normalized)
            normalized_name = self.normalize_name(name)
            if normalized_name in seen_names:
                continue

            # Extract address from div.text--14
            address_elem = item.find('div', class_='text--14')
            address = ''
            if address_elem:
                address = self.clean_text(address_elem.get_text())

            # Extract working hours from loc__other--long
            working_hours = ''
            hours_elem = item.find('div', class_='loc__other--long')
            if hours_elem:
                # Get the text, clean it
                hours_div = hours_elem.find('div')
                if hours_div:
                    working_hours = self.clean_text(hours_div.get_text())
                    # Clean up the hours format
                    working_hours = working_hours.replace('<br>', ' | ')

            # Extract service info from loc__other with icon--info
            service_info = ''
            service_elem = item.find('div', class_='loc__other')
            if service_elem and 'icon--info' in str(service_elem):
                # Get text but skip the icon
                service_info = self.clean_text(service_elem.get_text())

            # Get coordinates from the coords_map using the branch ID
            latitude = ''
            longitude = ''
            if data_id and data_id in coords_map:
                lat, lng = coords_map[data_id]
                latitude = str(lat)
                longitude = str(lng)

            branch = {
                'id': data_id,
                'name': name,
                'address': address,
                'latitude': latitude,
                'longitude': longitude,
                'working_hours': working_hours,
                'service_info': service_info
            }

            branches.append(branch)

            # Mark this ID and name as seen
            if data_id:
                seen_ids.add(data_id)
            seen_names.add(normalized_name)

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'id', 'name', 'address', 'latitude', 'longitude', 'working_hours', 'service_info'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Unibank branches page...")
        html = self.fetch_page()

        print("Extracting coordinates from JavaScript data...")
        coords_map = self.extract_coordinates(html)

        print("Extracting branch data from page...")
        self.branches = self.extract_branches(html, coords_map)

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
    scraper = UnibankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
