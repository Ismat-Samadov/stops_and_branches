import requests
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

def fetch_stops():
    """
    Fetch all bus stops from the Ayna API and save to JSON file.
    """
    url = "https://map-api.ayna.gov.az/api/stop/getAll"

    try:
        print("Fetching stops data from API...")
        response = requests.get(url)
        response.raise_for_status()

        stops_data = response.json()
        print(f"Successfully fetched {len(stops_data) if isinstance(stops_data, list) else 'unknown number of'} stops")

        # Ensure data directory exists
        os.makedirs(os.path.join(ROOT_DIR, 'data'), exist_ok=True)

        # Save to JSON file
        output_path = os.path.join(ROOT_DIR, 'data', 'stops.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stops_data, f, ensure_ascii=False, indent=2)

        print(f"Stops data saved to {output_path}")
        return stops_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching stops data: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

if __name__ == "__main__":
    fetch_stops()
