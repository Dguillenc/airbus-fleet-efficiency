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

# Consumo aproximado en kg de combustible por hora de vuelo (crucero).
# Fuentes: documentación pública de Airbus/Boeing y reportes operativos
# recopilados en docs/metodologia_co2.md. Cifras marcadas (*) son estimadas
# por interpolación entre modelos similares, no medición directa.
FUEL_BURN_KG_H = {
    "A320": 2500,
    "A319": 2300,
    "A321": 2700,
    "A320NEO": 2100,
    "A321NEO": 2300,
    "A330": 5000,
    "A350": 5700,   # (*)
    "A380": 11500,
    "737": 2400,    # (*)
    "737 MAX": 2100,  # (*)
    "747": 10000,
    "777": 7500,
    "787": 5500,    # (*)
}

CO2_PER_KG_FUEL = 3.16  # kg de CO2 por kg de combustible quemado (ICAO/IATA)

def match_fuel_burn(model):
    if pd.isna(model):
        return None
    model_upper = str(model).upper()
    for key, value in FUEL_BURN_KG_H.items():
        if key in model_upper:
            return value
    return None

def build_gold():
    conn = psycopg2.connect(**DB_PARAMS)
    query = """
        SELECT icao24, callsign, origin_country, manufacturer, model,
               baro_altitude, velocity, captured_at
        FROM silver.clean_flights
        WHERE manufacturer IN ('Airbus', 'Boeing')
    """
    df = pd.read_sql(query, conn)
    conn.close()

    df["estimated_fuel_burn_kg_h"] = df["model"].apply(match_fuel_burn)
    df["estimated_co2_kg_h"] = df["estimated_fuel_burn_kg_h"] * CO2_PER_KG_FUEL

    df = df.rename(columns={"baro_altitude": "altitude_m", "velocity": "velocity_ms"})
    df = df.dropna(subset=["estimated_fuel_burn_kg_h"])

    final_cols = [
        "manufacturer", "model", "icao24", "callsign", "origin_country",
        "altitude_m", "velocity_ms", "estimated_fuel_burn_kg_h",
        "estimated_co2_kg_h", "captured_at"
    ]
    return df[final_cols]

def clean_value(v):
    if isinstance(v, float) and pd.isna(v):
        return None
    return v

def load_to_gold(df):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    insert_query = """
        INSERT INTO gold.flight_efficiency (
            manufacturer, model, icao24, callsign, origin_country,
            altitude_m, velocity_ms, estimated_fuel_burn_kg_h,
            estimated_co2_kg_h, captured_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = []
    for record in df.to_dict(orient="records"):
        row = tuple(clean_value(record[col]) for col in df.columns)
        rows.append(row)

    cur.executemany(insert_query, rows)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Insertadas {len(rows)} filas en gold.flight_efficiency")

if __name__ == "__main__":
    df = build_gold()
    print(f"Filas con consumo estimado: {len(df)}")
    load_to_gold(df)