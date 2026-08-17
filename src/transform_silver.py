import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "dbname": "fleet_efficiency",
    "user": "airbus_user",
    "password": os.getenv("DB_PASSWORD"),
}

AIRCRAFT_DB_PATH = "data/reference/aircraftDatabase.csv"

def load_aircraft_reference():
    df = pd.read_csv(
        AIRCRAFT_DB_PATH,
        usecols=["icao24", "manufacturername", "model"],
        low_memory=False
    )
    df["icao24"] = df["icao24"].str.strip().str.lower()
    return df

def classify_manufacturer(name):
    if pd.isna(name):
        return None
    name = str(name).lower()
    if "airbus" in name:
        return "Airbus"
    if "boeing" in name:
        return "Boeing"
    return "Other"

def fetch_bronze_data():
    conn = psycopg2.connect(**DB_PARAMS)
    query = """
        SELECT icao24, callsign, origin_country, longitude, latitude,
               baro_altitude, velocity, time_position
        FROM bronze.raw_flights
        WHERE longitude IS NOT NULL AND latitude IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def transform():
    print("Cargando referencia de aeronaves...")
    aircraft_ref = load_aircraft_reference()

    print("Leyendo datos de bronze...")
    flights = fetch_bronze_data()
    flights["icao24"] = flights["icao24"].str.strip().str.lower()

    print("Cruzando datos...")
    merged = flights.merge(aircraft_ref, on="icao24", how="left")
    merged["manufacturer"] = merged["manufacturername"].apply(classify_manufacturer)
    merged["is_airbus"] = merged["manufacturer"] == "Airbus"
    merged["is_boeing"] = merged["manufacturer"] == "Boeing"
    merged["captured_at"] = pd.to_datetime(merged["time_position"], unit="s")

    final_cols = [
        "icao24", "callsign", "origin_country", "longitude", "latitude",
        "baro_altitude", "velocity", "manufacturer", "model",
        "is_airbus", "is_boeing", "captured_at"
    ]
    final_df = merged[final_cols].copy()

    print(f"Filas a insertar: {len(final_df)}")
    return final_df

def clean_value(v):
    # Convierte cualquier NaN (float) a None real de Python.
    if isinstance(v, float) and pd.isna(v):
        return None
    if pd.isna(v) if not isinstance(v, (list, tuple)) else False:
        return None
    return v

def load_to_silver(df):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    insert_query = """
        INSERT INTO silver.clean_flights (
            icao24, callsign, origin_country, longitude, latitude,
            baro_altitude, velocity, manufacturer, model,
            is_airbus, is_boeing, captured_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for record in df.to_dict(orient="records"):
        row = tuple(clean_value(record[col]) for col in df.columns)
        rows.append(row)

    cur.executemany(insert_query, rows)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Insertadas {len(rows)} filas en silver.clean_flights")

if __name__ == "__main__":
    df = transform()
    load_to_silver(df)