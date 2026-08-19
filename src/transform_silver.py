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


def print_data_quality_report(merged_df, total_rows):
    """Imprime un resumen de calidad del cruce con la base de referencia
    de aeronaves, para poder auditar cuánta información se perdió o
    quedó incompleta en cada ejecución del pipeline."""
    no_match = merged_df["manufacturername"].isna().sum()
    no_manufacturer_classified = merged_df["manufacturer"].isna().sum()
    no_model = merged_df["model"].isna().sum()
    duplicated_icao24 = merged_df["icao24"].duplicated().sum()

    pct_no_match = (no_match / total_rows * 100) if total_rows else 0
    pct_no_manufacturer = (no_manufacturer_classified / total_rows * 100) if total_rows else 0
    pct_no_model = (no_model / total_rows * 100) if total_rows else 0

    print("--- Informe de calidad de datos (cruce con referencia de aeronaves) ---")
    print(f"Total de observaciones procesadas: {total_rows}")
    print(f"Sin match en la base de aeronaves (icao24 desconocido): {no_match} ({pct_no_match:.1f}%)")
    print(f"Sin fabricante clasificado: {no_manufacturer_classified} ({pct_no_manufacturer:.1f}%)")
    print(f"Sin modelo identificado: {no_model} ({pct_no_model:.1f}%)")
    print(f"icao24 duplicados en la muestra: {duplicated_icao24}")
    print("-------------------------------------------------------------------")


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

    print_data_quality_report(merged, total_rows=len(flights))

    final_cols = [
        "icao24", "callsign", "origin_country", "longitude", "latitude",
        "baro_altitude", "velocity", "manufacturer", "model",
        "is_airbus", "is_boeing", "captured_at"
    ]
    final_df = merged[final_cols].copy()

    print(f"Filas a insertar: {len(final_df)}")
    return final_df


def clean_value(v):
    if isinstance(v, float) and pd.isna(v):
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