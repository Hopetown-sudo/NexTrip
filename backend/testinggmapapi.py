import requests
import os
api_key = os.getenv("GOOGLE_MAP_API_KEY")

def get_geocode(api_key, address):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'OK':
            location = data['results'][0]['geometry']['location']
            print(f"Address: {address}")
            print(f"Latitude: {location['lat']}")
            print(f"Longitude: {location['lng']}")
        else:
            print("Error:", data.get('status'))
    else:
        print(f"HTTP Error: {response.status_code}")


address = "1600 Amphitheatre Parkway, Mountain View, CA"

import requests

def get_trip_data(origin, destination, api_key):
    # Endpoint for Google Maps Directions API
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"

    # Parameters for the API request
    params = {
        "origin": origin,
        "destination": destination,
        "key": api_key
    }

    # Sending the request
    response = requests.get(endpoint, params=params)

    # Check for a successful response
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK":
            # Extracting trip details
            route = data["routes"][0]["legs"][0]
            distance = route["distance"]["text"]
            duration = route["duration"]["text"]
            start_address = route["start_address"]
            end_address = route["end_address"]

            print(f"Trip from {start_address} to {end_address}")
            print(f"Distance: {distance}")
            print(f"Duration: {duration}")
        else:
            print(f"Error: {data['status']} - {data.get('error_message', 'No details available')}")
    else:
        print(f"HTTP Error: {response.status_code}")


# Example usage
origin = "130 Statler Dr, Ithaca, NY"
destination = "151 3rd St, San Francisco, CA"

get_trip_data(origin, destination, api_key)

# get_geocode(api_key, address)