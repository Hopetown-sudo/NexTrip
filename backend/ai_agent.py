import openai
import os
from typing import Optional

openai.api_key = os.getenv("OPENAI_API_KEY")

def infer_car_specs_from_ai(car_make: str, car_model: str, year: Optional[str] = None) -> dict:
    """
    Use OpenAI to infer car fuel efficiency and tank capacity.
    """
    prompt = (
        f"I am planning a road trip and I need to know the fuel efficiency and fuel tank capacity "
        f"for a {year or ''} {car_make} {car_model}. Provide the values in miles per gallon and gallons respectively."
    )

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert in vehicle specifications."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
    )

    answer = response.choices[0].message['content']
    return parse_car_specs(answer)

def parse_car_specs(answer: str) -> dict:
    """
    Parse the AI's response to extract fuel efficiency and tank capacity.
    """
    efficiency = None
    capacity = None

    if "miles per gallon" in answer:
        efficiency = float(answer.split("miles per gallon")[0].split()[-1])
    if "gallons" in answer:
        capacity = float(answer.split("gallons")[0].split()[-1])

    return {
        "fuel_efficiency": efficiency,
        "fuel_tank_capacity": capacity
    }