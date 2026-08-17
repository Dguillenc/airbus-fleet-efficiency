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

# Capacidad aproximada de asientos en configuración típica de una clase.
# Estimación basada en especificaciones públicas de Airbus/Boeing.
SEAT_CAPACITY = {
    "A320": 180,
    "A319": 140,
    "A321": 220,
    "A320NEO": 180,
    "A321NEO": 220,
    "A330": 280,
    "A350": 325,
    "A380": 525,
    "737": 189,
    "737 MAX": 200,
    "747": 410,
    "777": 350,
    "787": 290,
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


def match_seat_capacity(model):
    if pd.isna(model):
        return None
    model_upper = str(model).upper()
    for key, value in SEAT_CAPACITY.items():
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

    df["seat_capacity"] = df["model"].apply(match_seat_capacity)

        # Velocidad viene en m/s desde OpenSky -> convertimos a km/h
    velocity_kmh = df["velocity"] * 3.6

    # Solo calculamos eficiencia de crucero para vuelos con velocidad realista
    # (>= 200 km/h). Por debajo de eso, el avión está en tierra, rodando,
    # despegando o aterrizando, y el ratio CO2/km deja de tener sentido físico.
    MIN_CRUISE_SPEED_KMH = 200
    valid_speed_mask = velocity_kmh >= MIN_CRUISE_SPEED_KMH

    df["co2_per_km"] = None
    df["co2_per_seat_km"] = None

    df.loc[valid_speed_mask, "co2_per_km"] = (
        df.loc[valid_speed_mask, "estimated_co2_kg_h"] / velocity_kmh[valid_speed_mask]
    )
    df.loc[valid_speed_mask, "co2_per_seat_km"] = (
        df.loc[valid_speed_mask, "co2_per_km"] / df.loc[valid_speed_mask, "seat_capacity"]
    )

    excluded_by_speed = (~valid_speed_mask).sum()
    print(f"Excluidos {excluded_by_speed} registros por velocidad no realista (<{MIN_CRUISE_SPEED_KMH} km/h)")

    df = df.rename(columns={"baro_altitude": "altitude_m", "velocity": "velocity_ms"})

    # Excluir registros con inconsistencia fabricante/modelo conocida
    # en la base de datos comunitaria de OpenSky (ej. "Airbus" + modelo "737").
    inconsistent_mask = (
        ((df["manufacturer"] == "Airbus") & (df["model"].str.contains("737", na=False))) |
        ((df["manufacturer"] == "Boeing") & (df["model"].str.contains("A3", na=False)))
    )
    inconsistent_count = inconsistent_mask.sum()
    if inconsistent_count > 0:
        print(f"Excluidas {inconsistent_count} filas por inconsistencia fabricante/modelo")
    df = df[~inconsistent_mask]

    df = df.dropna(subset=["estimated_fuel_burn_kg_h"])

    final_cols = [
        "manufacturer", "model", "icao24", "callsign", "origin_country",
        "altitude_m", "velocity_ms", "estimated_fuel_burn_kg_h",
        "estimated_co2_kg_h", "co2_per_km", "seat_capacity",
        "co2_per_seat_km", "captured_at"
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
            estimated_co2_kg_h, co2_per_km, seat_capacity,
            co2_per_seat_km, captured_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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