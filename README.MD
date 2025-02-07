# NexTrip Gen-AI enhanced Trip Planning Application

This project is designed to help long-haul drivers by recommending rest stops at regular intervals along their route. The app uses **Python (FastAPI)** for the backend and **Google Maps APIs** for route and location services. An AI-powered chatbot provides tailored stop suggestions.

---

## Features

- **Route Planning:** Input start and destination points to calculate optimal routes.
- **Personalized Recommendations:** AI suggests rest stops based on preferences.
- **Chatbot Interaction:** Get tailored suggestions through a conversational interface.

---

## Tech Stack

### Backend

- **Python (FastAPI)**
- **Google Maps APIs** (Directions, Places, Distance Matrix)
- **Uvicorn** for ASGI server

*(Frontend details to be added later)*

---

## Setup Instructions

### Prerequisites

- **Python 3.8+**
- **Google Cloud API Key**

### Backend Setup

1. Navigate to the backend folder.
2. Install Python dependencies:
   ```sh
   pip install fastapi uvicorn python-dotenv
   ```
3. Create a `.env` file and add your API keys:
   ```env
   GOOGLE_MAPS_KEY=your_google_maps_api_key
   ```
4. Run the FastAPI server:
   ```sh
   uvicorn main:app --reload
   ```
5. Access the API at `http://127.0.0.1:8000`.

---

## API Endpoints

- **GET /:** Basic health check.
- **GET /route:** Fetch route data between two points.
- **POST /recommend:** Get personalized rest stop recommendations.

---

## Environment Variables

Create `.env` files for sensitive data like API keys.

### Example `.env` for Backend

```env
GOOGLE_MAPS_KEY=your_google_maps_api_key
```

---

## License

This project is licensed under the CC0 1.0 Universal License. Please read the license document information carefully.

---

*(Frontend setup instructions to be added later)*

