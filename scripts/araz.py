#!/usr/bin/env python3
"""
Araz Market Web Scraper
Extracts branch locations and details from arazmarket.az
"""

import csv
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import os


def scrape_araz_locations(url: str = "https://arazmarket.az/az/stores") -> List[Dict[str, str]]:
    """
    Scrape Araz market branch locations

    Args:
        url: URL of the Araz stores page

    Returns:
        List of dictionaries containing branch information
    """
    print(f"Fetching data from {url}...")

    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        response.encoding = 'utf-8'
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    branches = []

    # Check for Next.js data
    import json
    import re

    # Look for Next.js RSC (React Server Components) streaming data
    # The data is embedded in self.__next_f.push() calls
    print("\nExtracting data from Next.js streaming format...")

    # Find all self.__next_f.push() calls in the HTML
    push_pattern = r'self\.__next_f\.push\((\[.*?\])\)'
    matches = re.findall(push_pattern, response.text)

    print(f"Found {len(matches)} data chunks")

    # Parse each chunk and look for store data
    stores_found = []

    for match in matches:
        try:
            # Parse the array [index, data]
            chunk = json.loads(match)
            if len(chunk) >= 2:
                data_str = chunk[1]

                # Check if this chunk contains store data
                if isinstance(data_str, str) and ('"title"' in data_str and '"address"' in data_str and '"phone_number"' in data_str):
                    # This looks like store data
                    # Try to extract JSON objects from the string
                    # The data might be escaped JSON within a string

                    # Look for store objects pattern with coordinates
                    # Pattern includes: id, title, address, work_time, phone_number, lat, lon
                    store_pattern = r'\{"id":(\d+),"title":"([^"]+)","address":"([^"]+)","work_time":"([^"]+)","phone_number":"([^"]+)","lat":"([^"]+)","lon":"([^"]+)"[^}]*\}'

                    store_matches = re.finditer(store_pattern, data_str)

                    for store_match in store_matches:
                        # Extract escaped characters
                        name = store_match.group(2).replace('\\\\', '\\')
                        address = store_match.group(3).replace('\\\\', '\\')
                        hours = store_match.group(4).replace('\\\\', '\\')
                        phone = store_match.group(5).replace('\\\\', '\\')
                        latitude = store_match.group(6)
                        longitude = store_match.group(7)

                        branch_data = {
                            'name': name,
                            'address': address,
                            'phone': phone,
                            'hours': hours,
                            'latitude': latitude,
                            'longitude': longitude
                        }

                        # Check if we already have this store (avoid duplicates)
                        if not any(s['name'] == name and s['address'] == address for s in stores_found):
                            stores_found.append(branch_data)

        except Exception as e:
            # Skip chunks that can't be parsed
            continue

    if stores_found:
        print(f"Successfully extracted {len(stores_found)} stores from streaming data")
        for branch in stores_found:
            branches.append(branch)
            print(f"Extracted: {branch['name']}")

        return branches

    # Look for __NEXT_DATA__ script tag as fallback
    next_data_script = soup.find('script', id='__NEXT_DATA__')
    if next_data_script:
        try:
            data = json.loads(next_data_script.string)
            print("\nFound __NEXT_DATA__ - extracting store information...")

            # Navigate through the Next.js data structure to find stores
            # The structure is: props -> pageProps -> stores (or similar)
            page_props = data.get('props', {}).get('pageProps', {})

            # Try different possible keys where stores might be
            stores_data = None
            for key in ['stores', 'branches', 'locations', 'data', 'storesList']:
                if key in page_props:
                    stores_data = page_props[key]
                    print(f"Found stores data under key: {key}")
                    break

            if not stores_data:
                # Print available keys to help debug
                print(f"Available keys in pageProps: {list(page_props.keys())}")

            if stores_data and isinstance(stores_data, list):
                print(f"Found {len(stores_data)} stores in __NEXT_DATA__")

                for store in stores_data:
                    branch_data = {
                        'name': store.get('name', store.get('title', 'N/A')),
                        'address': store.get('address', store.get('location', '')),
                        'phone': store.get('phone', store.get('tel', '')),
                        'hours': store.get('hours', store.get('workingHours', store.get('working_hours', '')))
                    }
                    branches.append(branch_data)
                    print(f"Extracted: {branch_data['name']}")

                return branches

        except Exception as e:
            print(f"Error parsing __NEXT_DATA__: {e}")

    # If Next.js streaming data extraction didn't work, fall back to HTML parsing
    print("\nFalling back to HTML parsing (may not work for dynamically loaded content)...")
    store_divs = soup.find_all('div', class_='page_list__v5vEU')

    if not store_divs:
        store_divs = soup.find_all('div', class_='accardion_accardionItem__Fyf_W')

    print(f"Found {len(store_divs)} branches in HTML")

    for store_div in store_divs:
        try:
            # Find the accordion item
            accordion = store_div.find('div', class_='accardion_accardionItem__Fyf_W')
            if not accordion:
                continue

            # Extract name from the title toggle
            title_toggle = accordion.find('div', class_='accardion_accardionTitleToggle___WyGP')
            name_span = title_toggle.find('span') if title_toggle else None
            name = name_span.text.strip() if name_span else "N/A"

            # Find the content section
            content = accordion.find('div', class_='accardion_accardionContent__Vlwtt')
            if not content:
                continue

            # Extract address (first <p> tag)
            address_p = content.find('p')
            address = address_p.text.strip() if address_p else ""

            # Extract phone and hours from the options div
            options_div = content.find('div', class_='page_list_option__Cq36k')
            phone = ""
            hours = ""

            if options_div:
                # Extract phone
                phone_link = options_div.find('a', href=lambda x: x and x.startswith('tel:'))
                if phone_link:
                    phone = phone_link.text.strip()

                # Extract hours
                time_small = options_div.find('small')
                if time_small:
                    hours = time_small.text.strip()

            branch_data = {
                'name': name,
                'address': address,
                'phone': phone,
                'hours': hours
            }

            branches.append(branch_data)
            print(f"Extracted: {name}")

        except Exception as e:
            print(f"Error parsing branch: {e}")
            continue

    return branches


def save_to_csv(branches: List[Dict[str, str]], output_file: str) -> None:
    """
    Save branch data to CSV file

    Args:
        branches: List of branch dictionaries
        output_file: Path to output CSV file
    """
    if not branches:
        print("No data to save")
        return

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)

    fieldnames = ['name', 'address', 'phone', 'hours', 'latitude', 'longitude']

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"\nSuccessfully saved {len(branches)} branches to {output_file}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")


def main():
    """Main execution function"""
    print("=" * 60)
    print("Araz Market Branch Scraper")
    print("=" * 60)

    # Scrape data
    branches = scrape_araz_locations()

    if branches:
        # Save to CSV
        output_file = 'data/araz.csv'
        save_to_csv(branches, output_file)

        # Print summary
        print("\n" + "=" * 60)
        print("Summary:")
        print(f"Total branches: {len(branches)}")
        print("=" * 60)
    else:
        print("\nNo branches found or error occurred")


if __name__ == "__main__":
    main()
