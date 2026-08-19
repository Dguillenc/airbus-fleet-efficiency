# Metodología de cálculo: consumo, emisiones y eficiencia

Este documento detalla cómo se calculan las métricas de `gold.flight_efficiency`, sus fuentes y sus limitaciones. Se referencia desde el README principal y desde `src/transform_gold.py`.

---

## 1. Unidad de observación

Cada fila del dataset representa una **observación de estado de una aeronave** en un instante concreto (posición, velocidad, altitud), capturada desde el endpoint `/api/states/all` de OpenSky Network — **no un vuelo completo de origen a destino**. Un mismo vuelo puede aparecer varias veces si el pipeline lo captura en distintos instantes durante su recorrido.

## 2. Consumo de combustible estimado (`estimated_fuel_burn_kg_h`)

No es un dato telemétrico real de la aeronave — es una estimación de referencia asignada según la familia del modelo (A320, A321, 737, 747...), basada en:

- Documentación pública de Airbus y Boeing.
- Reportes operativos de referencia del sector.

| Familia | Consumo estimado (kg/h) | Fuente / tipo |
|---|---|---|
| A320 | 2.500 | Documentación pública Airbus |
| A319 | 2.300 | Documentación pública Airbus |
| A321 | 2.700 | Documentación pública Airbus |
| A320neo | 2.100 | Documentación pública Airbus (-15% vs ceo) |
| A321neo | 2.300 | Estimado por interpolación |
| A330 | 5.000 | Reportes operativos |
| A350 | 5.700 | Estimado por interpolación (*) |
| A380 | 11.500 | Reportes operativos |
| 737 | 2.400 | Estimado por interpolación (*) |
| 737 MAX | 2.100 | Estimado por interpolación (*) |
| 747 | 10.000 | Reportes operativos |
| 777 | 7.500 | Reportes operativos |
| 787 | 5.500 | Estimado por interpolación (*) |

(*) Sin cifra pública exacta localizada; estimado por comparación con modelos de capacidad/generación similar.

**Importante:** esta cifra es la misma para todas las observaciones de una misma familia, independientemente de la ruta, carga, condiciones meteorológicas o fase de vuelo. No representa el consumo real de ese vuelo concreto.

## 3. Emisiones de CO₂ (`estimated_co2_kg_h`)
estimated_co2_kg_h = estimated_fuel_burn_kg_h × 3.16


El factor **3,16 kg de CO₂ por kg de combustible quemado** es el estándar de conversión para combustible de aviación (Jet A-1) usado por ICAO/IATA.

## 4. Eficiencia estimada en crucero (`co2_per_seat_km`)
co2_per_km = estimated_co2_kg_h / velocidad_km_h
co2_per_seat_km = co2_per_km / capacidad_asientos


**Qué mide realmente:** intensidad de emisión estimada en fase de crucero, bajo la velocidad instantánea observada en el momento de la captura — no el consumo real del vuelo completo puerta a puerta.

**Limitaciones explícitas:**
- Usa la **velocidad instantánea** capturada, no la velocidad media del vuelo. Dos observaciones del mismo modelo, mismo consumo de referencia y misma capacidad pueden dar `co2_per_seat_km` distinto simplemente por diferencias de velocidad en el instante de captura.
- Se excluyen observaciones con velocidad < 200 km/h (fases de despegue, aterrizaje y rodaje), donde el ratio pierde sentido físico. Esto significa que la métrica **no incluye** el consumo, típicamente mayor, de esas fases.
- Usa **capacidad de asientos teórica** (configuración típica publicada por el fabricante), no la ocupación real de ese vuelo concreto.

**Capacidad de asientos usada por familia:**

| Familia | Asientos (config. típica) |
|---|---|
| A320 | 180 |
| A319 | 140 |
| A321 | 220 |
| A330 | 280 |
| A350 | 325 |
| A380 | 525 |
| 737 | 189 |
| 737 MAX | 200 |
| 747 | 410 |
| 777 | 350 |
| 787 | 290 |

## 5. Limitación estadística: sesgo de composición de flota

Las medias agregadas por fabricante (Airbus vs Boeing) están influidas por qué familias de avión aparecen en la muestra y en qué proporción — no todos los modelos tienen el mismo peso real en la flota mundial ni en el tráfico capturado. Por tanto, una diferencia entre fabricantes en la media agregada **no debe interpretarse como una conclusión causal o universal** sobre qué fabricante es "más eficiente" en general. Una comparación más rigurosa exigiría:

- Comparar familias equivalentes por capacidad/rango (ej. A320 vs 737, A330/A350 vs 787).
- Ponderar por igual cada familia, en vez de por cada observación individual.

## 6. Calidad de datos: inconsistencias detectadas y tratadas

Se detectó que, en un pequeño porcentaje de registros (~0,3%), el fabricante y el modelo declarados en la base de datos de referencia de OpenSky son contradictorios (p. ej. fabricante "Airbus" con modelo conteniendo "737"). Estos registros se excluyen explícitamente en `transform_gold.py`.

## 7. Resumen de qué mide y qué no mide este dataset

**Sí mide (razonablemente bien):**
- Diferencias relativas de intensidad de emisión estimada entre familias de avión, bajo un modelo de consumo consistente.
- Patrón de tráfico geográfico capturado por la red de receptores ADS-B de OpenSky.

**No mide:**
- Consumo real telemétrico de un vuelo específico.
- Emisiones de un vuelo completo (incluye solo fase de crucero, no despegue/aterrizaje).
- Eficiencia ajustada por ocupación real de pasajeros.
- Una conclusión estadísticamente robusta sobre qué fabricante es "mejor", dado el sesgo de composición de flota.

## 8. Cobertura del cruce con la base de aeronaves

En una ejecución representativa, aproximadamente el **56% de las observaciones capturadas** no encuentran coincidencia en la base de datos de referencia de aeronaves (`icao24` desconocido). Esto es esperable dado que la base de OpenSky es comunitaria y no exhaustiva, y una parte significativa del tráfico capturado corresponde a aviación privada, militar u otras aeronaves fuera del alcance de este análisis (comercial Airbus/Boeing). Este dato se calcula e imprime automáticamente en cada ejecución del pipeline (`src/transform_silver.py`), permitiendo auditar la cobertura real de cada corrida.