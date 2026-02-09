#!/usr/bin/env python3
"""
Azərbaycan Fəhlə Bankı (AFB) Branch Scraper
Fetches branch data from AFB's website and saves to CSV.
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from typing import List, Dict, Tuple, Optional


class AFBScraper:
    """Scraper for AFB branch locations."""

    PAGE_URL = "https://afb.az/filiallar"
    OUTPUT_FILE = "data/afb_branches.csv"

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
            ' r-nu': '',  # Remove district info as it can confuse geocoder
            ' r.': '',
            ' küç.': ' küçəsi',
            ' pros.': ' prospekti',
            ' pr.': ' prospekti',
            ' mәh.': ' məhəllə',
            'Bakı şəhər': 'Baku',
            'Sumqayit şəhər': 'Sumqayit',
            'Gəncə şəhər': 'Ganja',
            'Qəbələ şəhər': 'Qabala',
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
        elif 'Sumqayit' in address:
            city = 'Sumqayit'
        elif 'Gəncə' in address or 'Ganja' in address:
            city = 'Ganja'
        elif 'Qəbələ' in address or 'Qabala' in address:
            city = 'Qabala'

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

        # Find the service network list
        branch_list = soup.find('ul', class_='service_network_list')
        if not branch_list:
            print("Warning: Could not find service network list")
            return branches

        # Find all branch items
        branch_items = branch_list.find_all('li')

        print(f"Found {len(branch_items)} branches in HTML")

        for item in branch_items:
            # Extract city class (city_8, city_127, etc.)
            city_class = None
            for cls in item.get('class', []):
                if cls.startswith('city_'):
                    city_class = cls
                    break

            # Extract branch name from h4
            name_elem = item.find('h4')
            name = ''
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            # Skip if no name
            if not name:
                continue

            # Get all paragraphs
            all_p = item.find_all('p')

            # First p without class is the address
            address = ''
            phone = ''
            email = ''
            working_hours = ''

            for p in all_p:
                p_class = p.get('class', [])
                text = self.clean_text(p.get_text())

                if 'work_hour_p' not in p_class and not address:
                    # This is the address
                    address = text
                elif 'work_hour_p' in p_class:
                    # Extract phone, email, or working hours
                    if text.startswith('Tel:'):
                        phone = text.replace('Tel:', '').strip()
                    elif text.startswith('E-mail:'):
                        email = text.replace('E-mail:', '').strip()
                    elif text.startswith('İş rejimi:'):
                        working_hours = text.replace('İş rejimi:', '').strip()

            # Geocode the address to get coordinates
            print(f"\nGeocoding branch: {name}")
            latitude, longitude = self.geocode_address(address)

            # Rate limiting: wait 1 second between requests (Nominatim usage policy)
            time.sleep(1)

            branch = {
                'city_class': city_class or '',
                'name': name,
                'address': address,
                'phone': phone,
                'email': email,
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
            'city_class', 'name', 'address', 'phone', 'email', 'working_hours', 'latitude', 'longitude'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching AFB branches page...")
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
    scraper = AFBScraper()
    scraper.run()


if __name__ == "__main__":
    main()
