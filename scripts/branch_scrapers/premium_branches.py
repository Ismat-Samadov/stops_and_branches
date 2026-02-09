#!/usr/bin/env python3
"""
Premium Bank Azerbaijan Branch Scraper
Fetches branch data from Premium Bank's website and saves to CSV.
"""

import requests
from bs4 import BeautifulSoup
import csv
import re
from typing import List, Dict


class PremiumBankScraper:
    """Scraper for Premium Bank branch locations."""

    PAGE_URL = "https://www.premiumbank.az/az/service-network/"
    OUTPUT_FILE = "data/premium_branches.csv"

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
        # Clean up whitespace
        text = ' '.join(text.split())
        return text.strip()

    def extract_branches(self, html_content: str) -> List[Dict]:
        """Extract branch data from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        branches = []

        # Find all list items with data-type attribute
        location_items = soup.find_all('li', {'data-type': True})

        print(f"Found {len(location_items)} locations in HTML")

        for item in location_items:
            # Only include branches, skip ATMs
            data_type = item.get('data-type', '')
            if data_type != 'branch':
                continue

            # Extract coordinates
            latitude = item.get('data-lat', '').strip()
            longitude = item.get('data-lng', '').strip()

            # Extract name from <strong> tag
            name_elem = item.find('strong')
            name = ''
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            # Extract details from <p> tag
            details_elem = item.find('p')
            details = ''
            if details_elem:
                details = details_elem.get_text()

            # Parse details
            license_number = ''
            address = ''
            working_hours = ''
            phone = ''
            whatsapp = ''
            email = ''
            info_center = ''
            fax = ''

            if details:
                # Extract license number
                license_match = re.search(r'Lisenziya\s*[№#]\s*(\d+[^<\n]*)', details)
                if license_match:
                    license_number = self.clean_text(license_match.group(1))

                # Extract address
                addr_match = re.search(r'Ünvan:\s*([^<\n]+?)(?=\s*(?:İş\s+saatı|$))', details)
                if addr_match:
                    address = self.clean_text(addr_match.group(1))

                # Extract working hours
                hours_match = re.search(r'İş\s+saatı:\s*([^<\n]+)', details)
                if hours_match:
                    working_hours = self.clean_text(hours_match.group(1))

                # Extract phone
                phone_match = re.search(r'Tel\.?:\s*([^\n<]+?)(?=\s*(?:WhatsApp|Elektron|Məlumat|Faks|$))', details)
                if phone_match:
                    phone = self.clean_text(phone_match.group(1))

                # Extract WhatsApp
                whatsapp_match = re.search(r'WhatsApp:\s*([^\n<]+)', details)
                if whatsapp_match:
                    whatsapp = self.clean_text(whatsapp_match.group(1))

                # Extract email from the <a> tag in details_elem
                if details_elem:
                    email_elem = details_elem.find('a', href=re.compile(r'^mailto:'))
                    if email_elem:
                        email = email_elem.get_text().strip()

                # Extract info center
                info_match = re.search(r'Məlumat\s+mərkəzi:\s*([^\n<]+)', details)
                if info_match:
                    info_center = self.clean_text(info_match.group(1))

                # Extract fax
                fax_match = re.search(r'Faks:\s*([^\n<]+)', details)
                if fax_match:
                    fax = self.clean_text(fax_match.group(1))

            branch = {
                'name': name,
                'license_number': license_number,
                'address': address,
                'latitude': latitude,
                'longitude': longitude,
                'working_hours': working_hours,
                'phone': phone,
                'whatsapp': whatsapp,
                'email': email,
                'info_center': info_center,
                'fax': fax,
            }

            branches.append(branch)

        return branches

    def save_to_csv(self, branches: List[Dict]):
        """Save branch data to CSV file."""
        if not branches:
            print("No branches found to save.")
            return

        fieldnames = [
            'name', 'license_number', 'address', 'latitude', 'longitude',
            'working_hours', 'phone', 'whatsapp', 'email', 'info_center', 'fax'
        ]

        with open(self.OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches)

        print(f"Saved {len(branches)} branches to {self.OUTPUT_FILE}")

    def run(self):
        """Main execution method."""
        print("Fetching Premium Bank branches page...")
        html = self.fetch_page()

        print("Extracting branch data from page...")
        self.branches = self.extract_branches(html)

        print(f"\nExtracted {len(self.branches)} branches (ATMs excluded)")

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
    scraper = PremiumBankScraper()
    scraper.run()


if __name__ == "__main__":
    main()
