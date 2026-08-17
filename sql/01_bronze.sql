CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE bronze.raw_flights (
    id SERIAL PRIMARY KEY,
    icao24 VARCHAR(10),
    callsign VARCHAR(20),
    origin_country VARCHAR(100),
    time_position BIGINT,
    last_contact BIGINT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    baro_altitude DOUBLE PRECISION,
    velocity DOUBLE PRECISION,
    true_track DOUBLE PRECISION,
    raw_payload JSONB,
    ingested_at TIMESTAMP DEFAULT NOW()
);