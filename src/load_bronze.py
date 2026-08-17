import os
import json
import psycopg2
from dotenv import load_dotenv
from extract import fetch_states

load_dotenv()

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "dbname": "fleet_efficiency",
    "user": "airbus_user",
    "password": os.getenv("DB_PASSWORD"),
}

INSERT_QUERY = """
    INSERT INTO bronze.raw_flights (
        icao24, callsign, origin_country, time_position, last_contact,
        longitude, latitude, baro_altitude, velocity, true_track, raw_payload
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

def load_states_to_bronze():
    data = fetch_states()
    states = data.get("states", [])

    if not states:
        print("No hay vuelos para insertar.")
        return

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    rows_inserted = 0
    for state in states:
        icao24 = state[0]
        callsign = state[1].strip() if state[1] else None
        origin_country = state[2]
        time_position = state[3]
        last_contact = state[4]
        longitude = state[5]
        latitude = state[6]
        baro_altitude = state[7]
        velocity = state[9]
        true_track = state[10]

        cur.execute(INSERT_QUERY, (
            icao24, callsign, origin_country, time_position, last_contact,
            longitude, latitude, baro_altitude, velocity, true_track,
            json.dumps(state)
        ))
        rows_inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Insertados {rows_inserted} vuelos en bronze.raw_flights")

if __name__ == "__main__":
    load_states_to_bronze()