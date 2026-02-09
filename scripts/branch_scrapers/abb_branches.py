#!/usr/bin/env python3
"""
Scrape ABB Bank Azerbaijan branch data from POST endpoint with full details

This scraper uses the Next.js React Server Component endpoint that returns
detailed branch information including coordinates, directors, working hours,
phone numbers, and nearby metro stations.

Endpoint: https://abb-bank.az/filiallar (POST)
"""

import requests
import json
import csv
import os
import re

def extract_branches_from_rsc(response_text):
    """Extract branch data from React Server Component response"""
    branches = []

    try:
        # RSC format: "1:[{...}]" followed by newline
        lines = response_text.split('\n')
        branches_data = None
        for line in lines:
            if line.startswith('1:'):
                json_str = line[2:]  # Remove "1:" prefix
                branches_data = json.loads(json_str)
                break

        if not branches_data:
            print("  Could not find branch data in response")
            return []

        for branch in branches_data:
            # Flatten the nested structure
            flat_branch = {
                'id': branch.get('id'),
                'documentId': branch.get('documentId'),
                'title': branch.get('title'),
                'address': branch.get('address'),
                'director': branch.get('director'),
                'branch_code': branch.get('branch_code'),
                'locale': branch.get('locale'),
                'createdAt': branch.get('createdAt'),
                'updatedAt': branch.get('updatedAt'),
                'publishedAt': branch.get('publishedAt')
            }

            # Extract coordinates
            coords = branch.get('coordinates', {})
            if coords:
                flat_branch['latitude'] = coords.get('lat')
                flat_branch['longitude'] = coords.get('lng')
                flat_branch['coordinates_id'] = coords.get('id')

            # Extract work time
            work_times = branch.get('work_time', [])
            if work_times:
                flat_branch['work_time'] = ' | '.join([wt.get('text', '') for wt in work_times])

            # Extract phone numbers
            phones = branch.get('phone_numbers', [])
            if phones:
                flat_branch['phone_numbers'] = ' | '.join([p.get('text', '') for p in phones])

            # Extract emails
            emails = branch.get('emails', [])
            if emails:
                flat_branch['emails'] = ' | '.join([e.get('text', '') for e in emails])

            # Extract subway info
            subways = branch.get('subways', [])
            if subways:
                subway_info = []
                for subway in subways:
                    name = subway.get('name', '')
                    time = subway.get('time', '')
                    color = subway.get('color', '')
                    subway_info.append(f"{name} ({time}, {color} line)")
                flat_branch['nearby_metro'] = ' | '.join(subway_info)

            # Extract filter tags
            tags = branch.get('filter_tags', [])
            tag_keys = []
            tag_titles = []
            for tag in tags:
                tag_keys.append(tag.get('key', ''))
                tag_titles.append(tag.get('title', ''))

            flat_branch['has_weekend_hours'] = 'open_on_weekends' in tag_keys
            flat_branch['has_safe_box'] = 'safe_box' in tag_keys
            flat_branch['filter_tags'] = ' | '.join(tag_titles)

            # Extract services
            services = branch.get('services', [])
            if services:
                flat_branch['services'] = ' | '.join([str(s) for s in services])

            branches.append(flat_branch)

        print(f"  Extracted {len(branches)} branches from response")

    except Exception as e:
        print(f"  Error parsing response: {e}")

    return branches

def fetch_branches_by_filter(filter_key=None):
    """Fetch branches with a specific filter"""
    url = "https://abb-bank.az/filiallar"

    headers = {
        'Accept': 'text/x-component',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
        'Content-Type': 'text/plain;charset=UTF-8',
        'Origin': 'https://abb-bank.az',
        'Referer': 'https://abb-bank.az/filiallar',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'next-action': '7fc053e9d43a5d68d83fe22333abfefe6fcd5650ef',
        'next-router-state-tree': '%5B%22%22%2C%7B%22children%22%3A%5B%5B%22locale%22%2C%22az%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%5B%22slug%22%2C%22filiallar%22%2C%22oc%22%5D%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D%7D%2Cnull%2Cnull%5D'
    }

    # Prepare the request body
    if filter_key:
        body = json.dumps([filter_key])
        filter_name = filter_key
    else:
        body = json.dumps([])
        filter_name = "all"

    print(f"Fetching branches with filter: {filter_name}")

    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()

        # Ensure correct UTF-8 encoding
        response.encoding = 'utf-8'

        branches = extract_branches_from_rsc(response.text)
        return branches

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching data: {e}")
        return []

def main():
    try:
        all_branches = {}

        # Try different filters to get all branches
        filters = [
            None,  # All branches
            "open_on_weekends",  # Weekend branches
            "safe_box"  # Branches with safe boxes
        ]

        for filter_key in filters:
            branches = fetch_branches_by_filter(filter_key)

            # Deduplicate by documentId
            for branch in branches:
                doc_id = branch.get('documentId')
                if doc_id:
                    # Keep the branch with most data
                    if doc_id not in all_branches:
                        all_branches[doc_id] = branch
                    else:
                        # Count non-empty fields
                        current_fields = sum(1 for v in branch.values() if v)
                        existing_fields = sum(1 for v in all_branches[doc_id].values() if v)
                        if current_fields > existing_fields:
                            all_branches[doc_id] = branch

        branches_list = list(all_branches.values())

        if not branches_list:
            print("\nNo branches found!")
            return

        print(f"\nTotal unique branches: {len(branches_list)}")

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        # Collect all unique field names
        fieldnames = set()
        for branch in branches_list:
            fieldnames.update(branch.keys())

        # Sort fieldnames for consistent column order
        fieldnames = sorted(fieldnames)

        # Save to CSV file
        output_file = 'data/abb_branches.csv'
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(branches_list)

        print(f"Data saved to {output_file}")

        # Print first branch as example
        if branches_list:
            print("\nExample (first branch):")
            print(json.dumps(branches_list[0], ensure_ascii=False, indent=2))

        # Print summary
        print(f"\nFields in the data ({len(fieldnames)}):")
        for field in fieldnames:
            print(f"  - {field}")

        # Count branches with coordinates
        with_coords = sum(1 for b in branches_list if b.get('latitude') and b.get('longitude'))
        print(f"\nBranches with coordinates: {with_coords}/{len(branches_list)}")

        # Count branches with weekend hours
        weekend_branches = sum(1 for b in branches_list if b.get('has_weekend_hours'))
        print(f"Branches with weekend hours: {weekend_branches}")

        # Count branches with safe boxes
        safe_box_branches = sum(1 for b in branches_list if b.get('has_safe_box'))
        print(f"Branches with safe boxes: {safe_box_branches}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
