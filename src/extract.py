import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENSKY_USER = os.getenv("OPENSKY_USER")
OPENSKY_PASS = os.getenv("OPENSKY_PASS")

# Bounding box aproximado de Europa (lat_min, lon_min, lat_max, lon_max)
BBOX = {
    "lamin": 35.0,
    "lomin": -10.0,
    "lamax": 60.0,
    "lomax": 30.0
}

def fetch_states():
    url = "https://opensky-network.org/api/states/all"
    params = {
        "lamin": BBOX["lamin"],
        "lomin": BBOX["lomin"],
        "lamax": BBOX["lamax"],
        "lomax": BBOX["lomax"],
    }
    response = requests.get(
        url,
        params=params,
        auth=(OPENSKY_USER, OPENSKY_PASS)
    )
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    data = fetch_states()
    print(f"Vuelos recibidos: {len(data.get('states', []))}")
    print(data["states"][0] if data.get("states") else "Sin datos")