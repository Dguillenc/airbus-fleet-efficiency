import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from transform_gold import match_fuel_burn, match_seat_capacity

CSV_PATH = "data/gold/flight_efficiency.csv"


@pytest.fixture(scope="module")
def gold_df():
    """Carga el dataset Gold una única vez para todos los tests."""
    return pd.read_csv(CSV_PATH)


def test_file_not_empty(gold_df):
    """El dataset debe contener al menos una observación."""
    assert len(gold_df) > 0


def test_manufacturer_only_airbus_or_boeing(gold_df):
    """La capa Gold debe contener únicamente Airbus o Boeing."""
    valid_manufacturers = {"Airbus", "Boeing"}
    assert set(gold_df["manufacturer"].unique()).issubset(valid_manufacturers)


def test_velocity_is_non_negative(gold_df):
    """La velocidad no puede ser negativa."""
    assert (gold_df["velocity_ms"].dropna() >= 0).all()


def test_seat_capacity_is_positive(gold_df):
    """La capacidad de asientos, cuando existe, debe ser mayor que cero."""
    valid_capacity = gold_df["seat_capacity"].dropna()
    assert (valid_capacity > 0).all()


def test_fuel_burn_is_positive(gold_df):
    """El consumo estimado, cuando existe, debe ser mayor que cero."""
    valid_fuel = gold_df["estimated_fuel_burn_kg_h"].dropna()
    assert (valid_fuel > 0).all()


def test_co2_per_seat_km_is_non_negative(gold_df):
    """La eficiencia estimada, cuando existe, no puede ser negativa."""
    valid_efficiency = gold_df["co2_per_seat_km"].dropna()
    assert (valid_efficiency >= 0).all()


def test_no_manufacturer_model_mismatch(gold_df):
    """No deben quedar inconsistencias fabricante/modelo conocidas
    (ej. Airbus con modelo conteniendo '737')."""
    airbus_with_boeing_model = gold_df[
        (gold_df["manufacturer"] == "Airbus")
        & (gold_df["model"].str.contains("737", na=False))
    ]
    boeing_with_airbus_model = gold_df[
        (gold_df["manufacturer"] == "Boeing")
        & (gold_df["model"].str.contains("A3", na=False))
    ]
    assert len(airbus_with_boeing_model) == 0
    assert len(boeing_with_airbus_model) == 0


def test_critical_columns_not_fully_null(gold_df):
    """Las columnas críticas para el análisis no deben estar vacías del todo."""
    critical_columns = ["manufacturer", "model", "icao24", "estimated_co2_kg_h"]
    for col in critical_columns:
        assert gold_df[col].notna().any(), f"La columna {col} está completamente vacía"


def test_altitude_within_realistic_range(gold_df):
    """La altitud, cuando existe, debe estar en un rango físicamente posible.
    Se permite un margen bajo cero (aeropuertos bajo el nivel del mar +
    margen de error del sensor barométrico) y hasta 15.000 m (cubre
    aeronaves de aviación de negocios con techo de servicio elevado)."""
    valid_altitude = gold_df["altitude_m"].dropna()
    assert (valid_altitude >= -100).all()
    assert (valid_altitude <= 15000).all()


def test_a320neo_not_matched_as_a320():
    """Regresión: A320neo debe recibir su propio consumo (2100), no el
    del A320 genérico (2500), pese a que 'A320' es substring de 'A320NEO'."""
    assert match_fuel_burn("A320-NEO") == 2100
    assert match_fuel_burn("AIRBUS A320NEO") == 2100


def test_737_max_not_matched_as_737():
    """Regresión: 737 MAX debe recibir su propio consumo (2100), no el
    del 737 genérico (2400)."""
    assert match_fuel_burn("737 MAX 8") == 2100
    assert match_fuel_burn("BOEING 737 MAX") == 2100


def test_generic_a320_still_matches():
    """Un A320 sin sufijo NEO debe seguir recibiendo el valor genérico."""
    assert match_fuel_burn("A320-214") == 2500


def test_seat_capacity_respects_variant_priority():
    """Mismo problema de substring, aplicado a capacidad de asientos."""
    assert match_seat_capacity("A321-NEO") == 220
    assert match_seat_capacity("737 MAX 8") == 200