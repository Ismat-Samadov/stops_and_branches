import requests
import json
import os
import time

def fetch_bus_list():
    """
    Fetch the list of all bus IDs from the Ayna API.
    """
    url = "https://map-api.ayna.gov.az/api/bus/getBusList"

    try:
        print("Fetching bus list from API...")
        response = requests.get(url)
        response.raise_for_status()

        bus_list = response.json()
        print(f"Successfully fetched {len(bus_list)} buses")
        return bus_list

    except requests.exceptions.RequestException as e:
        print(f"Error fetching bus list: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None

def fetch_bus_details(bus_id):
    """
    Fetch detailed information for a specific bus ID.
    """
    url = f"https://map-api.ayna.gov.az/api/bus/getBusById?id={bus_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for bus ID {bus_id}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response for bus ID {bus_id}: {e}")
        return None

def fetch_all_bus_details():
    """
    Fetch details for all buses and save to JSON file.
    """
    # First, get the list of all bus IDs
    bus_list = fetch_bus_list()
    if not bus_list:
        print("Failed to fetch bus list. Exiting.")
        return

    # Fetch details for each bus
    all_bus_details = []
    total_buses = len(bus_list)

    print(f"\nFetching details for {total_buses} buses...")

    for idx, bus in enumerate(bus_list, 1):
        bus_id = bus['id']
        bus_number = bus['number']

        print(f"[{idx}/{total_buses}] Fetching bus #{bus_number} (ID: {bus_id})...", end=' ')

        details = fetch_bus_details(bus_id)

        if details:
            all_bus_details.append(details)
            print("✓")
        else:
            print("✗")

        # Add a small delay to avoid overwhelming the server
        time.sleep(0.1)

    print(f"\nSuccessfully fetched details for {len(all_bus_details)}/{total_buses} buses")

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Save to JSON file
    output_path = 'data/busDetails.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_bus_details, f, ensure_ascii=False, indent=2)

    print(f"Bus details saved to {output_path}")
    return all_bus_details

if __name__ == "__main__":
    fetch_all_bus_details()
