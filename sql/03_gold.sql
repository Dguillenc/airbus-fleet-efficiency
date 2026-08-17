CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE gold.flight_efficiency (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(50) NOT NULL,
    model VARCHAR(100),
    icao24 VARCHAR(10),
    callsign VARCHAR(20),
    origin_country VARCHAR(100),
    altitude_m DOUBLE PRECISION,
    velocity_ms DOUBLE PRECISION,
    estimated_fuel_burn_kg_h DOUBLE PRECISION,
    estimated_co2_kg_h DOUBLE PRECISION,
    captured_at TIMESTAMP,
    loaded_at TIMESTAMP DEFAULT NOW()
);