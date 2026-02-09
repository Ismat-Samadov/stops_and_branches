#!/usr/bin/env python3
"""
Scrape AccessBank Azerbaijan branch data from their service network page
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import os

def scrape_branches():
    url = "https://www.accessbank.az/az/our-bank/service-networks/"

    print("Fetching webpage...")
    response = requests.get(url)
    response.raise_for_status()

    print("Parsing HTML...")
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract TYPE information from JavaScript - this is the most reliable source
    branch_coords = set()
    atm_coords = set()
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'TYPE' in script.string:
            type_matches = re.findall(r"'coord':'([\d.,]+)'.*?'TYPE':'(branch|ATM)'", script.string)
            for coord, obj_type in type_matches:
                if obj_type == 'branch':
                    branch_coords.add(coord)
                elif obj_type == 'ATM':
                    atm_coords.add(coord)

    # Keep all coordinates that are marked as branch (even if they also have ATMs)
    print(f"Found {len(branch_coords)} branch coordinates, {len(atm_coords)} ATM coordinates")
    print(f"Branch locations to extract: {len(branch_coords)} (including branches with ATMs)")

    # Find all detail divs (branches and ATMs)
    branches = []
    all_divs = soup.find_all('div', {'data-role': 'objInfo', 'data-group': 'objListDetail'})

    for branch_div in all_divs:
        branch_data = {}

        # Extract data-id
        branch_data['id'] = branch_div.get('data-id', '')
        branch_data['target'] = branch_div.get('data-target', '')

        # Extract address and fax
        address_div = branch_div.find('div', class_='service-network__places__item_expanded__info')
        if address_div:
            divs = address_div.find_all('div')
            if divs:
                # First div is the address
                branch_data['address'] = divs[0].get_text(strip=True)
                # Second div might be fax
                if len(divs) > 1:
                    fax_text = divs[1].get_text(strip=True)
                    if 'Faks:' in fax_text:
                        branch_data['fax'] = fax_text.replace('Faks:', '').strip()

        # Extract coordinates from map button
        map_button = branch_div.find('div', {'data-group': 'switchBranchMap'})
        if map_button:
            coords = map_button.get('data-coord', '')
            if coords:
                # Only include if this coordinate has a branch (even if it also has an ATM)
                if coords not in branch_coords:
                    continue

                lat, lon = coords.split(',')
                branch_data['latitude'] = lat.strip()
                branch_data['longitude'] = lon.strip()
                branch_data['coordinates'] = coords
                branch_data['object_id'] = map_button.get('data-objid', '')

        # Extract Google Maps link
        google_link = branch_div.find('a', {'data-role': 'gmappoint'})
        if google_link:
            branch_data['google_maps_url'] = google_link.get('href', '')

        # Extract Waze link
        waze_link = branch_div.find('a', {'data-role': 'wazepoint'})
        if waze_link:
            branch_data['waze_url'] = waze_link.get('href', '')

        # Extract WhatsApp link
        whatsapp_div = branch_div.find('div', {'data-role': 'whatsapp'})
        if whatsapp_div:
            whatsapp_link = whatsapp_div.find('a', href=True)
            if whatsapp_link:
                branch_data['whatsapp_url'] = whatsapp_link.get('href', '')
                # Extract phone number from WhatsApp link
                whatsapp_match = re.search(r'wa\.me/(\d+)', whatsapp_link.get('href', ''))
                if whatsapp_match:
                    branch_data['whatsapp_number'] = whatsapp_match.group(1)

        # Extract working hours, phone, and opening date
        extra_div = branch_div.find('div', class_='service-network__places__item_expanded__extra')
        if extra_div:
            worktime_items = extra_div.find_all('div', class_='branch-worktime__item')
            for item in worktime_items:
                title_div = item.find('div', class_='branch-worktime__title')
                subtitle_div = item.find('div', class_='branch-worktime__subtitle')

                if title_div and subtitle_div:
                    title = title_div.get_text(strip=True)
                    subtitle = subtitle_div.get_text(strip=True)

                    if 'İş vaxtı' in title or 'vaxt' in title.lower():
                        branch_data['working_hours'] = subtitle
                    elif 'Tel' in title:
                        branch_data['phone'] = subtitle
                    elif 'Açılış tarixi' in title or 'tarixi' in title.lower():
                        branch_data['opening_date'] = subtitle

        # Extract services
        service_div = branch_div.find('div', {'data-role': 'service'})
        if service_div:
            service_text = service_div.get_text(strip=True)
            if service_text:
                branch_data['services'] = service_text

        # Only add if we have coordinates (branches only)
        if 'coordinates' in branch_data:
            branches.append(branch_data)

    # Deduplicate branches by coordinates, keeping the one with most data
    unique_branches = {}
    for branch in branches:
        coord = branch['coordinates']

        # If this coord not seen yet, or this branch has more data than existing
        if coord not in unique_branches:
            unique_branches[coord] = branch
        else:
            # Count non-empty fields in current and existing
            current_fields = sum(1 for v in branch.values() if v)
            existing_fields = sum(1 for v in unique_branches[coord].values() if v)

            # Keep the one with more data
            if current_fields > existing_fields:
                unique_branches[coord] = branch

    return list(unique_branches.values())

def main():
    try:
        branches = scrape_branches()

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        # Collect all unique field names from all branches
        fieldnames = set()
        for branch in branches:
            fieldnames.update(branch.keys())

        # Sort fieldnames for consistent column order
        fieldnames = sorted(fieldnames)

        # Save to CSV file
        output_file = 'data/ab_branches.csv'
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            if branches:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(branches)

        print(f"\nSuccessfully scraped {len(branches)} branches")
        print(f"Data saved to {output_file}")

        # Print first branch as example
        if branches:
            print("\nExample (first branch):")
            print(json.dumps(branches[0], ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
