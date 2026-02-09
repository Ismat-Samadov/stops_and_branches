#!/usr/bin/env python3
"""
Rahat Market Web Scraper
Extracts branch locations and details from rahatmarket.az
"""

import csv
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import os
import re


def scrape_rahat_locations(url: str = "https://rahatmarket.az/az/map") -> List[Dict[str, str]]:
    """
    Scrape Rahat market branch locations

    Args:
        url: URL of the Rahat stores map page

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

    print("\nExtracting store data from JavaScript...")

    # Find all script tags and look for the locations array
    scripts = soup.find_all('script')

    for script in scripts:
        if script.string and 'var locations' in script.string:
            script_content = script.string

            # Extract the locations array using regex
            # The JavaScript structure is: [new google.maps.LatLng(lat, lng), 'name', '<a ...>address</a>']
            # We need to extract all three parts

            # First, try to match the complete pattern with both name and address
            # The name is in the second position, address is inside the anchor tag
            full_pattern = r'\[new google\.maps\.LatLng\(([\d.]+),\s*([\d.]+)\),\s*["\']([^"\']+)["\'],\s*["\']<a[^>]*>([^<]+)</a>["\']'

            full_matches = re.findall(full_pattern, script_content, re.DOTALL)

            print(f"Found {len(full_matches)} stores with full details (name + address)")

            if full_matches:
                for match in full_matches:
                    latitude = match[0]
                    longitude = match[1]
                    name = match[2].replace('\\', '').strip()
                    address = match[3].replace('\\', '').strip()

                    branch_data = {
                        'name': name if name else 'Rahat Market',
                        'address': address,
                        'phone': '',
                        'hours': '',
                        'latitude': latitude,
                        'longitude': longitude
                    }

                    branches.append(branch_data)
                    print(f"Extracted: {name}")
            else:
                # Fallback: extract just coordinates and names
                print("Full pattern didn't match, trying name-only pattern...")
                name_pattern = r'\[new google\.maps\.LatLng\(([\d.]+),\s*([\d.]+)\),\s*["\']([^"\']+)["\']'

                name_matches = re.findall(name_pattern, script_content)
                print(f"Found {len(name_matches)} stores with name pattern")

                for match in name_matches:
                    latitude = match[0]
                    longitude = match[1]
                    text = match[2].replace('\\', '').strip()

                    # Separate name and address
                    # Format: "Rahat Market (address)" or just "address"
                    name = 'Rahat Market'
                    address = ''

                    if text.startswith('Rahat Market'):
                        # Extract content from parentheses if present
                        paren_match = re.search(r'Rahat Market\s*\(([^)]*)\)', text)
                        if paren_match:
                            address = paren_match.group(1).strip()
                        else:
                            # No parentheses, might have trailing text
                            address = text.replace('Rahat Market', '').strip()
                    else:
                        # Text doesn't start with "Rahat Market", use it as address
                        address = text

                    branch_data = {
                        'name': name,
                        'address': address,
                        'phone': '',
                        'hours': '',
                        'latitude': latitude,
                        'longitude': longitude
                    }

                    branches.append(branch_data)
                    print(f"Extracted: {name} - {address[:50]}{'...' if len(address) > 50 else ''}")

            break

    if not branches:
        print("\nWarning: Could not find location data in JavaScript")
        print("Attempting alternative extraction methods...")

        # Try to find marker links as fallback
        marker_links = soup.find_all('a', class_='marker-link')
        print(f"Found {len(marker_links)} marker links")

        for link in marker_links:
            name = link.get_text(strip=True)
            marker_id = link.get('data-markerid', '')

            if name and name != 'Rahat Market':
                branch_data = {
                    'name': name,
                    'address': '',
                    'phone': '',
                    'hours': '',
                    'latitude': '',
                    'longitude': ''
                }

                branches.append(branch_data)
                print(f"Extracted: {name}")

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
    print("Rahat Market Branch Scraper")
    print("=" * 60)

    # Scrape data
    branches = scrape_rahat_locations()

    if branches:
        # Save to CSV
        output_file = 'data/rahat.csv'
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
