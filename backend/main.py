from fastapi import FastAPI, HTTPException
from models import TripData, UserPreferences
from route_planning import get_route, modify_route_with_waypoints, find_gas_stations
from ai_agent import infer_car_specs_from_ai

app = FastAPI()

@app.post("/plan_trip")
async def plan_trip(trip_data: TripData, preferences: UserPreferences):
    """
    Plan the trip by generating a route and refueling plan.
    """
    try:
        # Step 1: Get route data from Google Maps
        route_data = get_route(trip_data.origin, trip_data.destination)

        # Step 2: Infer car specs using AI
        if not preferences.car_make or not preferences.car_model:
            raise HTTPException(status_code=400, detail="Car make and model are required.")
        
        car_specs = infer_car_specs_from_ai(preferences.car_make, preferences.car_model, preferences.year)

        # Step 3: Identify refueling points
        refuel_points = [{"lat": step['end_location']['lat'], "lng": step['end_location']['lng']}
                         for step in route_data['legs'][0]['steps'][:2]]  # Example points

        # Step 4: Find gas stations near refuel points
        waypoints = []
        for point in refuel_points:
            location_str = f"{point['lat']},{point['lng']}"
            gas_stations = find_gas_stations(location_str)
            if gas_stations:
                waypoints.append(gas_stations[0])

        # Step 5: Modify the route with waypoints
        modified_route = modify_route_with_waypoints(trip_data.origin, trip_data.destination, waypoints)

        # Step 6: Return the modified route and refueling plan
        return {
            "route": modified_route,
            "waypoints": waypoints,
            "car_specs": car_specs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))