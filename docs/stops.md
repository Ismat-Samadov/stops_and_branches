# stops.py

## Overview
Python script that fetches all bus stop data from the Ayna Transport API and saves it to a JSON file.

## Purpose
This script retrieves comprehensive information about all public transport stops in the Baku transportation system, including stop codes, names, geographic coordinates, and transport hub status.

## API Endpoint
```
GET https://map-api.ayna.gov.az/api/stop/getAll
```

## Output
- **File**: `data/stops.json`
- **Format**: JSON array
- **Total Records**: ~3,841 stops

## Data Structure

Each stop object contains:

```json
{
  "id": 1732,
  "code": "1001631",
  "name": "Yeni Türkan qәs.",
  "nameMonitor": "Yeni Türkan qәs.",
  "utmCoordX": "0",
  "utmCoordY": "0",
  "longitude": "50.15006",
  "latitude": "40.378864",
  "isTransportHub": false
}
```

### Fields Description

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Unique identifier for the stop |
| `code` | String | Official stop code (e.g., "1001631") |
| `name` | String | Stop name in Azerbaijani |
| `nameMonitor` | String | Stop name for display monitors |
| `utmCoordX` | String | UTM X coordinate (currently "0") |
| `utmCoordY` | String | UTM Y coordinate (currently "0") |
| `longitude` | String | Geographic longitude |
| `latitude` | String | Geographic latitude |
| `isTransportHub` | Boolean | Whether the stop is a major transport hub |

## Usage

### Basic Usage
```bash
python scripts/stops.py
```

### Expected Output
```
Fetching stops data from API...
Successfully fetched 3841 stops
Stops data saved to data/stops.json
```

## Functions

### `fetch_stops()`
Main function that orchestrates the data fetching process.

**Returns**:
- `list` or `dict`: The fetched stops data if successful
- `None`: If an error occurs

**Process**:
1. Sends GET request to the API endpoint
2. Validates the response
3. Creates the `data/` directory if it doesn't exist
4. Saves the response to `data/stops.json` with UTF-8 encoding
5. Returns the data or None on error

## Error Handling

The script handles the following error types:
- **Network Errors**: Connection issues, timeouts
- **HTTP Errors**: Invalid status codes (4xx, 5xx)
- **JSON Decode Errors**: Invalid JSON response
- **File System Errors**: Permission issues, disk space

## Dependencies

```python
import requests  # For HTTP requests
import json      # For JSON parsing and writing
import os        # For file system operations
```

### Installation
```bash
pip install requests
```

## Features

- UTF-8 encoding support for Azerbaijani characters
- Automatic directory creation
- Comprehensive error handling
- Progress feedback to console
- Pretty-printed JSON output (indent=2)

## Use Cases

This data can be used for:
- Route optimization algorithms
- Stop proximity analysis
- Geographic mapping and visualization
- Transport hub identification
- Route planning applications
- Distance calculations between stops

## Notes

- The UTM coordinate fields are currently set to "0" in the API response
- The script uses `ensure_ascii=False` to properly handle Azerbaijani characters
- The output file is formatted with 2-space indentation for readability
- Total file size is approximately 418KB

## Example Integration

```python
import json

# Load stops data
with open('data/stops.json', 'r', encoding='utf-8') as f:
    stops = json.load(f)

# Find stops by name
def find_stop_by_name(name):
    return [stop for stop in stops if name.lower() in stop['name'].lower()]

# Get stop coordinates
def get_stop_coords(stop_id):
    stop = next((s for s in stops if s['id'] == stop_id), None)
    if stop:
        return (float(stop['latitude']), float(stop['longitude']))
    return None
```

## Related Scripts

- **busDetails.py**: Fetches detailed information for all bus routes including stops
