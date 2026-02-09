#!/usr/bin/env python3
"""
Turan Bank Azerbaijan Branch Scraper
Fetches branch data from Turan Bank's website and saves to CSV.
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


class TuranBankScraper:
    """Scraper for Turan Bank branch locations."""

    PAGE_URL = "https://www.turanbank.az/az/pages/2/155"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "turanbank_branches.csv")

    def __init__(self):
        self.branches = []

    def fetch_page(self) -> str:
        """Fetch the HTML page containing branch data."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # Disable SSL verification due to certificate issues
        response = requests.get(self.PAGE_URL, headers=headers, verify=False)
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
            ' ş.': ' şəhər',
            ' şəh.': ' şəhər',
            ' r-nu': '',  # Remove district info as it can confuse geocoder
            ' r.': '',
            ' küç.': ' küçəsi',
            ' pros.': ' prospekti',
            ' pr.': ' prospekti',
            ' mәh.': ' məhəllə',
            'Bakı şəhər': 'Baku',
            'Sumqayıt şəhər': 'Sumqayit',
            'Gəncə şəhər': 'Ganja',
            'Qəbələ şəhər': 'Qabala',
            'Zaqatala şəhər': 'Zagatala',
            'Tovuz şəhər': 'Tovuz',
            'Ağstafa şəhər': 'Agstafa',
            'Xaçmaz şəhər': 'Khachmaz',
            'Cəlilabad şəhər': 'Jalilabad',
            'Ağcabədi şəhər': 'Aghjabadi',
            'Göyçay şəhər': 'Goychay',
            'Qazax şəhər': 'Gazakh',
            'Xırdalan şəhər': 'Khirdalan',
        }

        processed = address
        for old, new in replacements.items():
            processed = processed.replace(old, new)

        # Add Azerbaijan to help with geocoding
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

        # Strategy 2: Try without building number (remove last part with numbers)
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
        # Extract city name
        city = ''
        if 'Bakı' in address or 'Baku' in address:
            city = 'Baku'
        elif 'Sumqayıt' in address:
            city = 'Sumqayit'
        elif 'Gəncə' in address or 'Ganja' in address:
            city = 'Ganja'
        elif 'Zaqatala' in address:
            city = 'Zagatala'
        elif 'Tovuz' in address:
            city = 'Tovuz'
        elif 'Ağstafa' in address:
            city = 'Agstafa'
        elif 'Xaçmaz' in address:
            city = 'Khachmaz'
        elif 'Cəlilabad' in address:
            city = 'Jalilabad'
        elif 'Ağcabədi' in address:
            city = 'Aghjabadi'
        elif 'Göyçay' in address:
            city = 'Goychay'
        elif 'Qazax' in address:
            city = 'Gazakh'
        elif 'Xırdalan' in address:
            city = 'Khirdalan'
        elif 'Lökbatan' in address:
            city = 'Lokbatan'

        if city:
            # Try to extract street name (look for prospekt, küçə, etc.)
            street_match = re.search(r'([А-Яа-яƏəŞşÇçÜüÖöĞğİı\w\s]+(?:pros\.|pr\.|küç\.|küçəsi|prospekti))\s*\d*', address)
            if street_match:
                street = street_match.group(1)
                street = self.preprocess_address(street)
                query = f"{street}, {city}, Azerbaijan"
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

        # Try to find all h1 tags (each branch has an h1 with the branch name)
        all_h1 = soup.find_all('h1')
        print(f"Found {len(all_h1)} h1 tags in HTML")

        for h1 in all_h1:
            name = self.clean_text(h1.get_text())
            if not name:
                continue

            # Get the parent div and find all p tags within it
            parent = h1.find_parent('div')
            if not parent:
                continue

            address = ''
            working_hours = ''

            all_p = parent.find_all('p')
            for p in all_p:
                text = self.clean_text(p.get_text())

                # First p with "Ünvan:" is the address
                if 'Ünvan:' in text and not address:
                    # Remove "Ünvan:" prefix and postal code
                    address = text.replace('Ünvan:', '').strip()
                    # Remove postal code (AZXXXX,)
                    address = re.sub(r'^AZ\d+,\s*', '', address)

                # Working hours pattern
                elif 'Bazar ertəsi' in text or '9:00' in text:
                    if not working_hours:
                        working_hours = text

            if not name or not address:
                continue

            # Geocode the address to get coordinates
            print(f"\nGeocoding branch: {name}")
            latitude, longitude = self.geocode_address(address)

            # Rate limiting: wait 1 second between requests (Nominatim usage policy)
            time.sleep(1)

            branch = {
                'name': name,
                'address': address,
                'working_hours': working_hours,
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
            'name', 'address', 'working_hours', 'latitude', 'longitude'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Turan Bank branches page...")
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    scraper = TuranBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
