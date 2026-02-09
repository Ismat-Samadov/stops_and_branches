# busDetails.py

## Overview
Python script that fetches detailed information for all bus routes in the Baku public transportation system. It first retrieves the list of all buses, then iterates through each bus ID to fetch comprehensive route details, stops, and coordinate data.

## Purpose
This script provides complete route information including stop sequences, geographic coordinates for route visualization, fare information, carrier details, and bidirectional route data for route optimization and analysis.

## API Endpoints

### 1. Bus List Endpoint
```
GET https://map-api.ayna.gov.az/api/bus/getBusList
```
Returns all bus IDs and numbers.

### 2. Bus Details Endpoint
```
GET https://map-api.ayna.gov.az/api/bus/getBusById?id={bus_id}
```
Returns detailed information for a specific bus route.

## Output
- **File**: `data/busDetails.json`
- **Format**: JSON array
- **Total Records**: ~208-209 bus routes
- **File Size**: ~16MB

## Data Structure

Each bus object contains comprehensive route information:

```json
{
  "id": 145,
  "carrier": "Vətən.Az-Trans MMC",
  "number": "210",
  "firstPoint": "Türkan bağları",
  "lastPoint": "Hövsan qəs.",
  "routLength": 30,
  "paymentTypeId": 2,
  "cardPaymentDate": null,
  "tariff": 50,
  "regionId": 1,
  "workingZoneTypeId": 5,
  "paymentType": { ... },
  "region": { ... },
  "workingZoneType": { ... },
  "stops": [ ... ],
  "routes": [ ... ],
  "tariffStr": "0.50 AZN",
  "durationMinuts": 50
}
```

### Main Fields Description

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Unique bus route identifier |
| `carrier` | String | Transport company operating the route |
| `number` | String | Bus route number (e.g., "210", "108A") |
| `firstPoint` | String | Starting point of the route |
| `lastPoint` | String | End point of the route |
| `routLength` | Integer | Route length in kilometers |
| `paymentTypeId` | Integer | Payment method ID (1=Card, 2=Cash) |
| `tariff` | Integer | Fare in qəpik (50 = 0.50 AZN) |
| `regionId` | Integer | Region ID (1=Baku) |
| `workingZoneTypeId` | Integer | Zone type (5=Urban) |
| `tariffStr` | String | Formatted fare string |
| `durationMinuts` | Integer | Route duration in minutes |

### Nested Objects

#### PaymentType
```json
{
  "id": 2,
  "name": "Nəğd",
  "description": null,
  "isActive": true,
  "deactivedDate": null,
  "priority": 2
}
```

#### Stop Object
```json
{
  "id": 5856,
  "stopCode": "1001631",
  "stopName": "Yeni Türkan qәs.",
  "totalDistance": 30,
  "intermediateDistance": 0,
  "directionTypeId": 1,
  "busId": 145,
  "stopId": 1732,
  "stop": {
    "id": 1732,
    "code": "1001631",
    "name": "Yeni Türkan qәs.",
    "longitude": "50.15006",
    "latitude": "40.378864",
    "isTransportHub": false
  }
}
```

#### Route Object (with coordinates)
```json
{
  "id": 207,
  "code": "210",
  "destination": "Yeni Türkan qәs. - 89 saylı poçt şöbəsi",
  "directionTypeId": 1,
  "busId": 145,
  "flowCoordinates": [
    {"lat": 40.37881, "lng": 50.15003},
    {"lat": 40.37836, "lng": 50.15146}
  ]
}
```

## Usage

### Basic Usage
```bash
python scripts/busDetails.py
```

### Expected Output
```
Fetching bus list from API...
Successfully fetched 209 buses

Fetching details for 209 buses...
[1/209] Fetching bus #1 (ID: 1)... ✓
[2/209] Fetching bus #2 (ID: 2)... ✓
...
[209/209] Fetching bus #596 (ID: 209)... ✓

Successfully fetched details for 208/209 buses
Bus details saved to data/busDetails.json
```

## Functions

### `fetch_bus_list()`
Retrieves the complete list of bus routes.

**Returns**:
- `list`: Array of bus objects with `id` and `number` fields
- `None`: If an error occurs

**Example Response**:
```python
[
  {"id": 1, "number": "1"},
  {"id": 145, "number": "210"}
]
```

### `fetch_bus_details(bus_id)`
Fetches detailed information for a specific bus route.

**Parameters**:
- `bus_id` (int): The bus route ID

**Returns**:
- `dict`: Complete bus route information
- `None`: If an error occurs

### `fetch_all_bus_details()`
Main orchestration function that:
1. Fetches the bus list
2. Iterates through each bus ID
3. Fetches detailed information for each bus
4. Compiles all data into a single array
5. Saves to JSON file

**Returns**:
- `list`: Array of all bus details
- `None`: If bus list fetch fails

## Features

- **Progress Tracking**: Visual progress indicators with checkmarks (✓/✗)
- **Error Resilience**: Continues processing even if individual requests fail
- **Rate Limiting**: 0.1-second delay between requests to avoid server overload
- **UTF-8 Support**: Proper handling of Azerbaijani characters
- **Comprehensive Error Handling**: Network, HTTP, and JSON errors
- **Detailed Logging**: Shows bus number, ID, and status for each request

## Error Handling

The script handles:
- **Network Errors**: Connection timeouts, DNS failures
- **HTTP Errors**: 4xx/5xx status codes (e.g., 500 Internal Server Error for bus ID 96)
- **JSON Decode Errors**: Invalid JSON responses
- **File System Errors**: Permission and disk space issues

Failed requests are logged but don't stop the script execution.

## Dependencies

```python
import requests  # HTTP requests
import json      # JSON parsing and writing
import os        # File system operations
import time      # Rate limiting delays
```

### Installation
```bash
pip install requests
```

## Performance

- **Total Buses**: 209 routes
- **Success Rate**: 208/209 (99.5%)
- **Processing Time**: ~25-30 seconds
- **Request Rate**: ~10 requests/second
- **Output Size**: ~16MB

## Use Cases

This comprehensive dataset enables:

1. **Route Optimization**: Analyze route efficiency and suggest improvements
2. **Stop Coverage Analysis**: Identify service gaps or redundancies
3. **Geographic Visualization**: Plot routes on maps using flowCoordinates
4. **Fare Analysis**: Study pricing across different zones
5. **Service Planning**: Analyze route lengths and durations
6. **Network Analysis**: Study route overlaps and connections
7. **Carrier Performance**: Compare operators and service coverage

## Example Integration

```python
import json

# Load bus details
with open('data/busDetails.json', 'r', encoding='utf-8') as f:
    buses = json.load(f)

# Find bus by number
def find_bus(number):
    return next((bus for bus in buses if bus['number'] == number), None)

# Get all stops for a bus
def get_bus_stops(bus_id):
    bus = next((b for b in buses if b['id'] == bus_id), None)
    return bus['stops'] if bus else []

# Calculate total route distance
def get_route_distance(bus_id):
    bus = next((b for b in buses if b['id'] == bus_id), None)
    return bus['routLength'] if bus else 0

# Get buses by carrier
def get_buses_by_carrier(carrier_name):
    return [bus for bus in buses if carrier_name in bus['carrier']]

# Extract all unique stops
def get_all_unique_stops():
    stops = set()
    for bus in buses:
        for stop in bus.get('stops', []):
            stops.add((stop['stopId'], stop['stopName']))
    return list(stops)

# Get route coordinates for mapping
def get_route_coordinates(bus_id, direction=1):
    bus = next((b for b in buses if b['id'] == bus_id), None)
    if not bus:
        return []

    route = next((r for r in bus['routes'] if r['directionTypeId'] == direction), None)
    return route['flowCoordinates'] if route else []
```

## Direction Types

Routes include bidirectional data:
- **directionTypeId = 1**: Outbound direction (firstPoint → lastPoint)
- **directionTypeId = 2**: Inbound direction (lastPoint → firstPoint)

## Known Issues

- Bus ID 96 (number "144") returns a 500 Internal Server Error from the API
- Some routes may have incomplete coordinate data
- UTM coordinates in stop data are currently "0"

## Related Scripts

- **stops.py**: Fetches comprehensive stop information
- Can be used together for complete network analysis

## Notes

- The script includes rate limiting to prevent overwhelming the server
- All data is encoded in UTF-8 to preserve Azerbaijani characters
- JSON output is formatted with 2-space indentation for readability
- Processing time depends on network speed and API response times
