#!/usr/bin/env python3
"""
Yapi Kredi Bank Azerbaijan Branch Scraper
Fetches branch data from Yapi Kredi Bank's website and saves to CSV.
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


class YapiKrediBankScraper:
    """Scraper for Yapi Kredi Bank branch locations."""

    PAGE_URL = "https://www.yapikredi.com.az/az/filiallar"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "yapikredi_branches.csv")

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
            ' ş.': ' şəhər',
            ' şəh.': ' şəhər',
            'şəhəri': 'şəhər',
            ' r-nu': '',
            ' r.': '',
            'rayonu': '',
            ' küç.': ' küçəsi',
            ' pros.': ' prospekti',
            ' pr.': ' prospekti',
            ' mәh.': ' məhəllə',
            'Bakı şəhər': 'Baku',
            'Sumqayıt şəhər': 'Sumqayit',
            'Gəncə şəhər': 'Ganja',
        }

        processed = address
        for old, new in replacements.items():
            processed = processed.replace(old, new)

        # Remove postal codes and other metadata
        processed = re.sub(r'\d{3,4}-ci məhəllə,?\s*', '', processed)
        processed = re.sub(r'Azərbaycan,?\s*', '', processed)

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
        city = ''
        if 'Bakı' in address or 'Baku' in address:
            city = 'Baku'
        elif 'Sumqayıt' in address:
            city = 'Sumqayit'

        if city:
            # Try to extract street name
            street_match = re.search(r'([А-Яа-яƏəŞşÇçÜüÖöĞğİı\w\s]+(?:küç|küçəsi))\s*[,\d]', address)
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

        # Find all branch list items
        branch_list = soup.find('ul', class_='toggle_list')
        if not branch_list:
            print("Warning: Could not find branch list")
            return branches

        branch_items = branch_list.find_all('li')
        print(f"Found {len(branch_items)} branches in HTML")

        for item in branch_items:
            # Extract branch name from toggle_header
            header = item.find('div', class_='toggle_header')
            if not header:
                continue

            name_elem = header.find('span')
            if not name_elem:
                continue

            name = self.clean_text(name_elem.get_text())
            if not name:
                continue

            # Extract details from toggle_body
            body = item.find('div', class_=re.compile(r'toggle_body'))
            if not body:
                continue

            p_elem = body.find('p')
            if not p_elem:
                continue

            # Get all text content
            content = p_elem.get_text()

            # Parse the content
            address = ''
            phone = ''
            working_hours = ''

            # Extract address (after "Ünvan:")
            address_match = re.search(r'Ünvan:\s*([^<\n]+?)(?:\s*<br>|Tel:|$)', content, re.IGNORECASE)
            if address_match:
                address = self.clean_text(address_match.group(1))

            # Extract phone (after "Tel:")
            phone_match = re.search(r'Tel:\s*([^<\n]+?)(?:\s*<br>|24/7:|Call Center:|Faks:|$)', content, re.IGNORECASE)
            if phone_match:
                phone = self.clean_text(phone_match.group(1))

            # Extract working hours (after "İş qrafiki:" or "Həftə içi")
            hours_match = re.search(r'İş qrafiki:\s*([^<\n]+)', content, re.IGNORECASE)
            if hours_match:
                working_hours = self.clean_text(hours_match.group(1))
            else:
                # Try alternate pattern for some branches
                hours_match = re.search(r'(Həftə içi\s+\d+:\d+-\d+:\d+[^<\n]*)', content)
                if hours_match:
                    working_hours = self.clean_text(hours_match.group(1))

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
                'phone': phone,
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
            'name', 'address', 'phone', 'working_hours', 'latitude', 'longitude'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Yapi Kredi Bank branches page...")
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
    scraper = YapiKrediBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
