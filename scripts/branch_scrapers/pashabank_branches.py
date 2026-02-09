#!/usr/bin/env python3
"""
Pasha Bank Azerbaijan Branch Scraper
Fetches branch data from Pasha Bank's website and saves to CSV.
"""

import os
import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from typing import List, Dict, Tuple, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class PashaBankScraper:
    """Scraper for Pasha Bank branch locations."""

    PAGE_URL = "https://www.pashabank.az/branches/lang,az/"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "pashabank_branches.csv")

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

    def preprocess_address(self, address: str) -> str:
        """Preprocess address for better geocoding results."""
        # Replace Azerbaijani abbreviations with full words
        replacements = {
            ' küç.': ' küçəsi',
            ' pr.': ' prospekti',
            'şöbəsi': '',
            'filialı': '',
            'şəhəri': 'şəhər',
            'Bakı şəhər': 'Baku',
            'Gəncə şəhər': 'Ganja',
            'Zaqatala şəhər': 'Zagatala',
            'Quba şəhər': 'Quba',
        }

        processed = address
        for old, new in replacements.items():
            processed = processed.replace(old, new)

        # Remove postal codes
        processed = re.sub(r',?\s*AZ\d+,?\s*', ', ', processed)
        # Remove "Azərbaycan"
        processed = re.sub(r',?\s*Azərbaycan\s*', '', processed)

        # Add Azerbaijan for better geocoding
        processed = f"{processed}, Azerbaijan"

        return processed

    def try_geocode(self, query: str) -> Optional[Tuple[str, str]]:
        """Try to geocode a single query string."""
        try:
            url = 'https://nominatim.openstreetmap.org/search'

            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'az',
            }

            headers = {
                'User-Agent': 'BankBranchScraper/1.0 (https://github.com/yourusername/branch_locations)'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data and len(data) > 0:
                lat = data[0].get('lat', '')
                lon = data[0].get('lon', '')
                if lat and lon:
                    return (str(lat), str(lon))

            return None

        except Exception:
            return None

    def geocode_address(self, address: str) -> Tuple[str, str]:
        """
        Geocode an address using Nominatim (OpenStreetMap).
        Tries multiple strategies to find coordinates.
        Returns (latitude, longitude) as strings, or ('', '') if geocoding fails.
        """
        if not address:
            return ('', '')

        # Strategy 1: Try full preprocessed address
        processed_address = self.preprocess_address(address)
        result = self.try_geocode(processed_address)
        if result:
            print(f"  ✓ Geocoded (full): {address[:40]}...")
            print(f"    -> {result}")
            return result

        time.sleep(0.5)

        # Strategy 2: Try without building number
        address_no_number = re.sub(r'\s*\d+[A-Za-z]?(/\d+)?$', '', address)
        if address_no_number != address:
            processed = self.preprocess_address(address_no_number)
            result = self.try_geocode(processed)
            if result:
                print(f"  ✓ Geocoded (street): {address[:40]}...")
                print(f"    -> {result}")
                return result

        time.sleep(0.5)

        # Strategy 3: Try just city and main street name
        city = ''
        if 'Bakı' in address or 'Baku' in address or 'Qaradağ' in address:
            city = 'Baku'
        elif 'Gəncə' in address or 'Ganja' in address:
            city = 'Ganja'
        elif 'Zaqatala' in address:
            city = 'Zagatala'
        elif 'Quba' in address:
            city = 'Quba'

        if city:
            # Try to extract street name
            street_match = re.search(r'([А-Яа-яƏəŞşÇçÜüÖöĞğİı\w\s]+(?:küç|küçəsi|pr\.|prospekti))', address)
            if street_match:
                street = street_match.group(1).strip()
                street_clean = street.replace('pr.', 'prospekti').replace('küç.', 'küçəsi')
                query = f"{street_clean}, {city}, Azerbaijan"
                result = self.try_geocode(query)
                if result:
                    print(f"  ✓ Geocoded (city+street): {address[:40]}...")
                    print(f"    -> {result}")
                    return result

                time.sleep(0.5)

            # Strategy 4: Try just the city center as last resort
            result = self.try_geocode(f"{city}, Azerbaijan")
            if result:
                print(f"  ✓ Geocoded (city center): {address[:40]}...")
                print(f"    -> {result}")
                return result

        print(f"  ✗ No coordinates found for: {address[:50]}...")
        return ('', '')

    def extract_branches(self, html_content: str) -> List[Dict]:
        """Extract branch data from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        branches = []

        # Find the overview container
        overview = soup.find('div', class_='overview')
        if not overview:
            print("Warning: Could not find overview container")
            return branches

        # Find all branch links
        branch_links = overview.find_all('a', class_='place')
        print(f"Found {len(branch_links)} branches in HTML")

        for link in branch_links:
            # Extract branch name from h3
            name_elem = link.find('h3', class_='name')
            if not name_elem:
                continue

            name = self.clean_text(name_elem.get_text())
            # Remove quotes from name
            name = name.strip('"')

            # Extract address from div
            address_elem = link.find('div', class_='address')
            if not address_elem:
                continue

            # Get address text, replacing <br> with space
            address_html = str(address_elem)
            address_soup = BeautifulSoup(address_html, 'html.parser')
            # Replace <br> tags with newlines
            for br in address_soup.find_all('br'):
                br.replace_with('\n')

            address = address_soup.get_text()
            # Join lines with comma
            address_lines = [line.strip() for line in address.split('\n') if line.strip()]
            address = ', '.join(address_lines)

            if not name or not address:
                continue

            # Geocode the address to get coordinates
            print(f"\nGeocoding branch: {name}")
            latitude, longitude = self.geocode_address(address)

            # Rate limiting: wait 1 second between requests
            time.sleep(1)

            branch = {
                'name': name,
                'address': address,
                'latitude': latitude,
                'longitude': longitude
            }

            branches.append(branch)

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'name', 'address', 'latitude', 'longitude'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Pasha Bank branches page...")
        html = self.fetch_page()

        print("Extracting branch data from page...")
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
            import json
            print(json.dumps(self.branches[0], ensure_ascii=False, indent=2))

        print("Done!")


def main():
    scraper = PashaBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
