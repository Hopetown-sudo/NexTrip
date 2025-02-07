import googlemaps
import os
GMAPS_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
gmaps = googlemaps.Client(key=GMAPS_API_KEY)
print (GMAPS_API_KEY)

def get_route(origin: str, destination: str):
    """
    Fetch route data from Google Maps API.
    """
    directions = gmaps.directions(origin, destination)
    if directions:
        return directions[0]
    else:
        raise Exception("No route found.")

def find_gas_stations(location: str, radius: int = 5000) -> list:
    """
    Find gas stations near a given location within a 5km radius.
    """
    places = gmaps.places_nearby(location=location, radius=radius, type='gas_station')
    return [place['name'] for place in places.get('results', [])]

def modify_route_with_waypoints(origin: str, destination: str, waypoints: list):
    """
    Modify the route by adding waypoints (gas stations) along the trip.
    """
    return gmaps.directions(origin, destination, waypoints=waypoints)
