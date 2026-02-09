#!/usr/bin/env python3
"""
ASB (Azerbaijan Savings Bank) Branch Scraper
Fetches branch data from ASB's website and saves to CSV.
"""

import os
import requests
from bs4 import BeautifulSoup
import csv
import re
import html
from typing import List, Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class ASBScraper:
    """Scraper for ASB Bank branch locations."""

    PAGE_URL = "https://www.asb.az/az/filiallar"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "asb_branches.csv")

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
        """Clean HTML entities and extra whitespace from text."""
        if not text:
            return ""

        # Decode HTML entities
        text = html.unescape(text)

        # Remove HTML tags
        text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)

        # Clean up whitespace
        text = ' '.join(text.split())

        return text.strip()

    def extract_branches(self, html_content: str) -> List[Dict]:
        """Extract branch data from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        branches = []

        # Find all map-point links
        map_points = soup.find_all('a', class_='map-point')

        print(f"Found {len(map_points)} locations in HTML (branches + ATMs)")

        for point in map_points:
            # Extract basic info from data attributes
            title = point.get('title', '').strip()

            # Skip ATMs - only include branches (filiallar)
            if title.startswith('ATM') or 'Test Terminal' in title:
                continue

            phone = point.get('data-phone', '').strip()
            worktime = self.clean_text(point.get('data-worktime', ''))
            address = self.clean_text(point.get('data-address', ''))
            lat_lng = point.get('data-lat_lng', '').strip()

            # Parse coordinates
            latitude = ''
            longitude = ''
            if lat_lng:
                coords = [c.strip() for c in lat_lng.split(',')]
                if len(coords) == 2:
                    latitude = coords[0]
                    longitude = coords[1]

            # Extract additional info from worktime field
            opening_date = ''
            license_number = ''
            activity_types = ''
            working_hours = worktime

            # Parse opening date
            opening_match = re.search(r'Filialın açılma tarixi\s*-\s*([\d.]+)', worktime)
            if opening_match:
                opening_date = opening_match.group(1).strip()

            # Parse license number
            license_match = re.search(r'Lisenziya nömrəsi\s*[–-]\s*([\d/]+)', worktime)
            if license_match:
                license_number = license_match.group(1).strip()

            # Parse activity types
            activity_match = re.search(r'Fəaliyyət növləri\s*[–-]\s*([^<\n]+?)(?=\s*(?:Filialın|$))', worktime)
            if activity_match:
                activity_types = activity_match.group(1).strip()

            # Extract just working hours (first line before other info)
            hours_match = re.search(r'İş vaxtı:\s*([^<\n]+?)(?=\s*(?:Fəaliyyət|$))', worktime)
            if hours_match:
                working_hours = f"İş vaxtı: {hours_match.group(1).strip()}"

            branch = {
                'name': title,
                'address': address,
                'latitude': latitude,
                'longitude': longitude,
                'phone': phone,
                'working_hours': working_hours,
                'activity_types': activity_types,
                'opening_date': opening_date,
                'license_number': license_number,
            }

            branches.append(branch)

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'name', 'address', 'latitude', 'longitude',
            'phone', 'working_hours', 'activity_types',
            'opening_date', 'license_number'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching ASB Bank branches page...")
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
    scraper = ASBScraper()
    scraper.run()


if __name__ == "__main__":
    main()
