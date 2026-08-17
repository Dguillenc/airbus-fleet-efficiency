CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE silver.clean_flights (
    id SERIAL PRIMARY KEY,
    icao24 VARCHAR(10) NOT NULL,
    callsign VARCHAR(20),
    origin_country VARCHAR(100),
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    baro_altitude DOUBLE PRECISION,
    velocity DOUBLE PRECISION,
    manufacturer VARCHAR(50),
    model VARCHAR(100),
    is_airbus BOOLEAN,
    is_boeing BOOLEAN,
    captured_at TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NOW()
);