from pydantic import BaseModel
from typing import List, Optional

# Input and output data models for the API
class TripData(BaseModel):
    origin: str
    destination: str

class UserPreferences(BaseModel):
    car_make: Optional[str] = None
    car_model: Optional[str] = None
    year: Optional[str] = None
    minimize_detour: bool = True
    preferred_stations: Optional[List[str]] = None