#!/usr/bin/env python3
"""
Ziraat Bank Azerbaijan Branch Scraper
Fetches branch data from Ziraat Bank's website and saves to CSV.
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from typing import List, Dict, Tuple, Optional


class ZiraatBankScraper:
    """Scraper for Ziraat Bank branch locations."""

    PAGE_URL = "https://ziraatbank.az/az/branches-atms"
    OUTPUT_FILE = "data/ziraatbank_branches.csv"

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
        # Fix typos first
        address = address.replace('rayou', 'rayonu')

        # Replace Azerbaijani abbreviations with full words
        replacements = {
            ' ş.': ' şəhər',
            ' şəh.': ' şəhər',
            ' şəh,': ' şəhər',
            'şəhəri': 'şəhər',
            ' r-nu': '',
            ' ray.': '',
            ' ray,': '',
            'rayonu': '',
            'Rayonu': '',
            ' küç.': ' küçəsi',
            ' pros.': ' prospekti',
            ' pr.': ' prospekti',
            'prospekti': 'prospekti',
            ' mәh.': ' məhəllə',
            'Bakı şəhər': 'Baku',
            'Sumqayıt şəhər': 'Sumqayit',
            'Gəncə şəhər': 'Ganja',
            'Quba şəhər': 'Quba',
            'Naxçıvan şəhər': 'Nakhchivan',
        }

        processed = address
        for old, new in replacements.items():
            processed = processed.replace(old, new)

        # Remove building/mall names and floor info
        processed = re.sub(r',?\s*\d+-ci mərtəbə\.?', '', processed)
        processed = re.sub(r',?\s*World Business Center', '', processed)
        processed = re.sub(r',?\s*Babək Plaza', '', processed)

        # Remove "MR" (Muxtar Respublika)
        processed = re.sub(r'\s*MR,?\s*', ' ', processed)

        # Add Azerbaijan to help with geocoding, but also add Baku if not specified
        if 'Baku' not in processed and 'Bakı' not in processed and \
           'Sumqayıt' not in processed and 'Gəncə' not in processed and \
           'Quba' not in processed and 'Naxçıvan' not in processed:
            processed = f"{processed}, Baku, Azerbaijan"
        else:
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
        elif 'Gəncə' in address or 'Ganja' in address:
            city = 'Ganja'
        elif 'Quba' in address:
            city = 'Quba'
        elif 'Naxçıvan' in address:
            city = 'Nakhchivan'
        elif 'Qaradağ' in address or 'Sədərək' in address:
            city = 'Baku'  # Qaradağ is a district in Baku

        if city:
            # Try to extract street name with better pattern
            street_match = re.search(r'([А-Яа-яƏəŞşÇçÜüÖöĞğİı\w\s]+(?:prospekti|pros\.|pr\.|küç|küçəsi))', address)
            if street_match:
                street = street_match.group(1).strip()
                # Clean up the street name
                street_clean = street.replace('pr.', 'prospekti').replace('pros.', 'prospekti').replace('küç.', 'küçəsi')
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

        # Find all branch containers
        acc_boxes = soup.find_all('div', class_='acc-box')
        print(f"Found {len(acc_boxes)} branches in HTML")

        for box in acc_boxes:
            # Extract branch name from h2
            h2 = box.find('h2')
            if not h2:
                continue

            name = self.clean_text(h2.get_text())
            if not name:
                continue

            # Extract details from acc-content
            content = box.find('div', class_='acc-content')
            if not content:
                continue

            # Find all p tags
            p_tags = content.find_all('p')

            address = ''
            phone = ''
            working_hours = ''

            for p in p_tags:
                text = p.get_text()

                # Extract address
                if 'Ünvan:' in text:
                    address = text.split('Ünvan:', 1)[1].strip()
                    address = self.clean_text(address)

                # Extract phone
                elif 'Tel:' in text:
                    phone = text.split('Tel:', 1)[1].strip()
                    phone = self.clean_text(phone)

                # Extract working hours
                elif 'İş vaxtı:' in text:
                    working_hours = text.split('İş vaxtı:', 1)[1].strip()
                    working_hours = self.clean_text(working_hours)

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
        print("Fetching Ziraat Bank branches page...")
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
    scraper = ZiraatBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
