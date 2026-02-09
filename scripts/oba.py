#!/usr/bin/env python3
"""
OBA Supermarket Web Scraper
Extracts branch locations and details from oba.az
"""

import csv
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import os


def scrape_oba_locations(url: str = "https://oba.az/branches/") -> List[Dict[str, str]]:
    """
    Scrape OBA supermarket branch locations

    Args:
        url: URL of the OBA branches page

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

    print("\nExtracting store data from HTML...")

    # Find all branch items with map coordinates
    branch_divs = soup.find_all('div', class_='js-map-coordinates')

    print(f"Found {len(branch_divs)} branches")

    for branch_div in branch_divs:
        try:
            # Extract coordinates from data attributes
            latitude = branch_div.get('data-lat', '')
            longitude = branch_div.get('data-lng', '')

            # Extract name from h3 tag
            name_h3 = branch_div.find('h3', class_='fs-16')
            name = name_h3.text.strip() if name_h3 else ''

            # Extract address/description from p tag
            address_p = branch_div.find('p', class_='color-gray')
            address = address_p.text.strip() if address_p else ''

            # If address is same as name or empty, leave it empty
            if address == name:
                address = ''

            branch_data = {
                'name': name,
                'address': address,
                'phone': '',     # Phone not visible in the provided HTML structure
                'hours': '',     # Hours not visible in the provided HTML structure
                'latitude': latitude,
                'longitude': longitude
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
    print("OBA Supermarket Branch Scraper")
    print("=" * 60)

    # Scrape data
    branches = scrape_oba_locations()

    if branches:
        # Save to CSV
        output_file = 'data/oba.csv'
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
