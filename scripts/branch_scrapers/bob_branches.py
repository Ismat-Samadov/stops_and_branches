#!/usr/bin/env python3
"""
Bank of Baku Branch Scraper
Fetches branch data from Bank of Baku's API and saves branches (filiali) to CSV.
"""

import os
import aiohttp
import asyncio
import csv
import re
from typing import List, Dict
from urllib.parse import quote

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class BankOfBakuScraper:
    """Scraper for Bank of Baku branch locations."""

    API_URL = "https://site-api.bankofbaku.com/categories/serviceNetwork/individual"
    OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "branches", "bob_branches.csv")

    def __init__(self):
        self.branches = []
        self.geocoding_delay = 1.0  # Delay between geocoding requests to be respectful

    async def fetch_data(self) -> dict:
        """Fetch data from Bank of Baku API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch data: HTTP {response.status}")

    async def geocode_address(self, session: aiohttp.ClientSession, address: str) -> tuple:
        """
        Geocode an address to get lat/long coordinates using Nominatim (OpenStreetMap).
        Returns (latitude, longitude) or (None, None) if geocoding fails.
        """
        if not address:
            return None, None

        # Add "Azerbaijan" to improve geocoding accuracy
        search_address = f"{address}, Azerbaijan"
        url = f"https://nominatim.openstreetmap.org/search?q={quote(search_address)}&format=json&limit=1"

        try:
            headers = {
                'User-Agent': 'BankOfBakuBranchScraper/1.0'  # Required by Nominatim
            }
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        lat = data[0].get('lat')
                        lon = data[0].get('lon')
                        return lat, lon
        except Exception as e:
            print(f"  Geocoding error for '{address}': {e}")

        return None, None

    def clean_html(self, html_text: str) -> str:
        """Remove HTML tags and decode HTML entities."""
        if not html_text:
            return ""

        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html_text)

        # Decode common HTML entities
        replacements = {
            '&laquo;': '«',
            '&raquo;': '»',
            '&ccedil;': 'ç',
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
        }

        for entity, char in replacements.items():
            text = text.replace(entity, char)

        return text.strip()

    def extract_branches(self, data: dict) -> List[Dict]:
        """Extract branch data from API response."""
        branches = []
        seen_addresses = {}  # Track by normalized address to avoid duplicates

        pages = data.get('payload', {}).get('pages', [])

        # Find the branch page
        for page in pages:
            if page.get('serviceNetworkType') == 'branch':
                info_groups = page.get('informationGroup', [])

                for info_group in info_groups:
                    list_groups = info_group.get('listGroup', [])

                    # Each list_group represents ONE branch with 3 language versions
                    for list_group in list_groups:
                        lists = list_group.get('lists', [])

                        # Check if this is a filial OR office (head office, administrative office)
                        is_location = False
                        for entry in lists:
                            title = self.clean_html(entry.get('title', ''))
                            # Include filiali and also offices (baş idarə, ofis)
                            if ('filial' in title.lower() or 'branch' in title.lower() or
                                'office' in title.lower() or 'ofis' in title.lower() or
                                'idarə' in title.lower()):
                                is_location = True
                                break

                        # Only process service locations
                        if not is_location:
                            continue

                        # Extract location from list_group level
                        location_str = list_group.get('location', '')
                        latitude = ''
                        longitude = ''

                        if location_str:
                            # Parse "lat, lon" or "lat,lon" format
                            coords = [c.strip() for c in location_str.split(',')]
                            if len(coords) == 2:
                                latitude = coords[0]
                                longitude = coords[1]

                        # Create branch entry
                        branch = {
                            'name_az': '',
                            'name_en': '',
                            'name_ru': '',
                            'address_az': '',
                            'address_en': '',
                            'address_ru': '',
                            'phone': '',
                            'fax': '',
                            'working_hours': '',
                            'services_az': '',
                            'services_en': '',
                            'services_ru': '',
                            'location': location_str,
                            'slug': '',
                            'latitude': latitude,
                            'longitude': longitude,
                        }

                        # Process each language version
                        for entry in lists:
                            language = entry.get('language', '')
                            title = self.clean_html(entry.get('title', ''))
                            address = entry.get('address', '')
                            services = entry.get('serviceNames', '')

                            # Update common fields from first entry
                            if not branch['phone']:
                                branch['phone'] = entry.get('phone', '') or ''
                            if not branch['fax']:
                                branch['fax'] = entry.get('fax', '') or ''
                            if not branch['working_hours']:
                                branch['working_hours'] = entry.get('workingHours', '') or ''
                            if not branch['slug']:
                                branch['slug'] = entry.get('slug', '') or ''

                            # Populate language-specific fields based on language field
                            if language == 'az':
                                branch['name_az'] = title
                                branch['address_az'] = address
                                branch['services_az'] = services
                            elif language == 'en':
                                branch['name_en'] = title
                                branch['address_en'] = address
                                branch['services_en'] = services
                            elif language == 'ru':
                                branch['name_ru'] = title
                                branch['address_ru'] = address
                                branch['services_ru'] = services

                        # Deduplicate by address (normalize by removing spaces and punctuation)
                        # Use Azerbaijani address as the key
                        normalized_addr = re.sub(r'[^\w]', '', branch['address_az'].lower())

                        if normalized_addr in seen_addresses:
                            # Duplicate found - skip it
                            print(f"  ⚠ Skipping duplicate: {branch['name_az']} at {branch['address_az']}")
                            continue

                        seen_addresses[normalized_addr] = True
                        branches.append(branch)

        return branches

    async def add_coordinates(self, branches: List[Dict]):
        """Add latitude and longitude coordinates to branches by geocoding addresses."""
        print("Geocoding addresses to get coordinates...")

        async with aiohttp.ClientSession() as session:
            for i, branch in enumerate(branches, 1):
                # Use English address if available, otherwise Azerbaijani
                address = branch.get('address_en') or branch.get('address_az') or branch.get('address_ru')

                if address:
                    print(f"  ({i}/{len(branches)}) Geocoding: {branch.get('name_en') or branch.get('name_az', 'Unknown')}")
                    lat, lon = await self.geocode_address(session, address)

                    if lat and lon:
                        branch['latitude'] = lat
                        branch['longitude'] = lon
                        print(f"    ✓ Found: {lat}, {lon}")
                    else:
                        print(f"    ✗ Could not geocode")

                    # Be respectful to Nominatim's rate limits
                    await asyncio.sleep(self.geocoding_delay)

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'name_az', 'name_en', 'name_ru',
            'address_az', 'address_en', 'address_ru',
            'latitude', 'longitude',
            'phone', 'fax', 'working_hours',
            'services_az', 'services_en', 'services_ru',
            'location', 'slug'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    async def run(self):
        """Main execution method."""
        print("Fetching Bank of Baku branch data...")
        data = await self.fetch_data()

        print("Extracting branch and office information...")
        self.branches = self.extract_branches(data)

        print(f"\nFound {len(self.branches)} locations (branches + offices)")

        # Count how many have coordinates
        with_coords = sum(1 for b in self.branches if b['latitude'] and b['longitude'])
        print(f"Locations with coordinates: {with_coords}/{len(self.branches)}")

        print("\nSaving to CSV...")
        self.save_to_csv(self.branches)

        print("Done!")


async def main():
    scraper = BankOfBakuScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
