import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

OPENSKY_CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID")
OPENSKY_CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET")

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

# Bounding box aproximado de Europa (lat_min, lon_min, lat_max, lon_max)
BBOX = {
    "lamin": 35.0,
    "lomin": -10.0,
    "lamax": 60.0,
    "lomax": 30.0
}

# Segundos antes de expirar en los que refrescamos el token de forma proactiva.
TOKEN_REFRESH_MARGIN = 30


class TokenManager:
    """Gestiona el ciclo de vida del token OAuth2, refrescándolo automáticamente
    cuando está a punto de expirar (los tokens de OpenSky duran 30 minutos)."""

    def __init__(self):
        self.token = None
        self.expires_at = None

    def get_token(self):
        if self.token and self.expires_at and datetime.now() < self.expires_at:
            return self.token
        return self._refresh()

    def _refresh(self):
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": OPENSKY_CLIENT_ID,
                "client_secret": OPENSKY_CLIENT_SECRET,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        self.token = data["access_token"]
        expires_in = data.get("expires_in", 1800)
        self.expires_at = datetime.now() + timedelta(seconds=expires_in - TOKEN_REFRESH_MARGIN)
        return self.token

    def headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}


# Instancia compartida — se reutiliza en todas las llamadas del pipeline
# dentro de una misma ejecución, evitando pedir un token nuevo cada vez.
tokens = TokenManager()


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
        headers=tokens.headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    data = fetch_states()
    print(f"Vuelos recibidos: {len(data.get('states', []))}")
    print(data["states"][0] if data.get("states") else "Sin datos")