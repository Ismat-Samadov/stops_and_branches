#!/usr/bin/env python3
"""
Bravo Supermarket Web Scraper
Extracts branch locations and details from bravosupermarket.az
"""

import csv
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import os


def scrape_bravo_locations(url: str = "https://www.bravosupermarket.az/branches/") -> List[Dict[str, str]]:
    """
    Scrape Bravo supermarket branch locations

    Args:
        url: URL of the Bravo branches page

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

    # Find all branch articles
    articles = soup.find_all('article', attrs={'data-lat': True, 'data-lng': True})

    print(f"Found {len(articles)} branches")

    for article in articles:
        try:
            # Extract basic info
            name_elem = article.find('h3')
            name = name_elem.text.strip() if name_elem else "N/A"

            # Extract all list items
            list_items = article.find_all('li')

            branch_type = ""
            phone = ""
            address = ""
            hours = ""

            for li in list_items:
                span = li.find('span')
                if span:
                    text = span.text.strip()

                    # Determine what type of info this is
                    if li.get('class') and 'location' in li.get('class'):
                        if not branch_type and text in ['Hiper', 'Super', 'Market', 'Ekspres', 'Premium']:
                            branch_type = text
                        else:
                            address = text
                    elif li.get('class') and 'phone' in li.get('class'):
                        phone = text
                    elif li.get('class') and 'time' in li.get('class'):
                        hours = text

            # Extract coordinates
            latitude = article.get('data-lat', '0')
            longitude = article.get('data-lng', '0')

            # Extract category ID
            category = article.get('data-category', '')

            # Map category IDs to types
            category_map = {
                '2237': 'Hiper',
                '2236': 'Super',
                '2235': 'Market',
                '2238': 'Ekspres'
            }

            if not branch_type and category in category_map:
                branch_type = category_map[category]

            # Extract Google Maps link
            google_maps_link = ""
            maps_link = article.find('a', class_='google-maps-link')
            if maps_link:
                google_maps_link = maps_link.get('href', '')

            branch_data = {
                'name': name,
                'type': branch_type,
                'phone': phone,
                'address': address,
                'hours': hours,
                'latitude': latitude,
                'longitude': longitude,
                'category_id': category,
                'google_maps_url': google_maps_link
            }

            branches.append(branch_data)
            print(f"Extracted: {name} ({branch_type})")

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

    fieldnames = ['name', 'type', 'phone', 'address', 'hours', 'latitude', 'longitude', 'category_id', 'google_maps_url']

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
    print("Bravo Supermarket Branch Scraper")
    print("=" * 60)

    # Scrape data
    branches = scrape_bravo_locations()

    if branches:
        # Save to CSV
        output_file = 'data/bravo.csv'
        save_to_csv(branches, output_file)

        # Print summary
        print("\n" + "=" * 60)
        print("Summary:")
        print(f"Total branches: {len(branches)}")

        # Count by type
        type_counts = {}
        for branch in branches:
            branch_type = branch['type'] or 'Unknown'
            type_counts[branch_type] = type_counts.get(branch_type, 0) + 1

        print("\nBranches by type:")
        for branch_type, count in sorted(type_counts.items()):
            print(f"  {branch_type}: {count}")
        print("=" * 60)
    else:
        print("\nNo branches found or error occurred")


if __name__ == "__main__":
    main()
