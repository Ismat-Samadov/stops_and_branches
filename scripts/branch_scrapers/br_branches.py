#!/usr/bin/env python3
"""
Bank Respublika Branch Scraper
Fetches branch data from Bank Respublika's website and saves to CSV.
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import html
import re
from typing import List, Dict


class BankRespublikaScraper:
    """Scraper for Bank Respublika branch locations."""

    PAGE_URL = "https://www.bankrespublika.az/az/branches"
    OUTPUT_FILE = "data/br_branches.csv"

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
        """Clean HTML entities and extra whitespace from text."""
        if not text:
            return ""

        # Decode HTML entities
        text = html.unescape(text)

        # Remove HTML tags
        text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'<\\?\/br>', ' ', text)  # Handle escaped tags
        text = re.sub(r'<[^>]+>', '', text)

        # Clean up whitespace
        text = ' '.join(text.split())

        return text.strip()

    def extract_branches(self, html_content: str) -> List[Dict]:
        """Extract branch data from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        branches = []

        # Find all list items with data-info attribute
        branch_items = soup.find_all('li', {'data-info': True})

        print(f"Found {len(branch_items)} locations in HTML")

        for item in branch_items:
            try:
                # Parse JSON from data-info attribute
                data_info_str = item.get('data-info', '')

                # The JSON is HTML-encoded, so we need to unescape it
                data_info_str = html.unescape(data_info_str)

                data = json.loads(data_info_str)

                # Check if this is a branch (not ATM)
                categories = data.get('categorylist', [])
                if 'branches' not in categories:
                    continue

                # Extract basic info
                title = data.get('title', '').strip()
                branch_id = data.get('id', '')
                shortstory = data.get('shortstory', '')

                # Parse shortstory to extract details
                address = ''
                phone = ''
                email = ''
                working_hours = ''
                creation_date = ''

                # Extract address
                addr_match = re.search(r'Ünvan:\s*([^<]+?)(?=\s*(?:Telefon:|$))', shortstory)
                if addr_match:
                    address = self.clean_text(addr_match.group(1))

                # Extract phone
                phone_match = re.search(r'Telefon:\s*([^<]+?)(?=\s*(?:E-mail:|$))', shortstory)
                if phone_match:
                    phone = self.clean_text(phone_match.group(1))

                # Extract email
                email_match = re.search(r'E-mail:\s*([^<\s]+)', shortstory)
                if email_match:
                    email = self.clean_text(email_match.group(1))

                # Extract working hours
                hours_match = re.search(r'İş vaxtı:\s*([^<]+?)(?=\s*(?:Yaradılma|$))', shortstory)
                if hours_match:
                    working_hours = self.clean_text(hours_match.group(1))

                # Extract creation date
                date_match = re.search(r'Yaradılma tarixi:\s*([^<]+)', shortstory)
                if date_match:
                    creation_date = self.clean_text(date_match.group(1))

                # Extract extras (coordinates, etc.)
                extras = data.get('extras', {})
                latitude = extras.get('lattitude', '')  # Note: API has typo "lattitude"
                longitude = extras.get('longitude', '')
                branch_code = extras.get('branchid', '')
                city_location = extras.get('citylocation', '')

                branch = {
                    'id': branch_id,
                    'name': title,
                    'address': address,
                    'latitude': latitude,
                    'longitude': longitude,
                    'phone': phone,
                    'email': email,
                    'working_hours': working_hours,
                    'creation_date': creation_date,
                    'branch_code': branch_code,
                    'city_location': city_location,
                }

                branches.append(branch)

            except json.JSONDecodeError as e:
                print(f"  Error parsing JSON for item: {e}")
                continue
            except Exception as e:
                print(f"  Error processing item: {e}")
                continue

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'id', 'name', 'address', 'latitude', 'longitude',
            'phone', 'email', 'working_hours', 'creation_date',
            'branch_code', 'city_location'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Bank Respublika branches page...")
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
            print(json.dumps(self.branches[0], ensure_ascii=False, indent=2))

        print("Done!")


def main():
    scraper = BankRespublikaScraper()
    scraper.run()


if __name__ == "__main__":
    main()
