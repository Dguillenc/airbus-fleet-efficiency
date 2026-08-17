<div align="center">

# ✈️ Airbus vs Boeing — Fleet Efficiency & CO₂ Analytics

**Pipeline de datos y dashboard de eficiencia/emisiones de flota Airbus vs Boeing, con datos reales de vuelos en vivo (OpenSky Network)**

[![Pipeline Status](https://github.com/Dguillenc/airbus-fleet-efficiency/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Dguillenc/airbus-fleet-efficiency/actions/workflows/pipeline.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-F2C811?logo=powerbi&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

</div>

---

## 📊 Vista previa del dashboard

> Emisiones estimadas de CO₂ por familia de avión y fabricante, actualizadas diariamente con datos reales de tráfico aéreo europeo.


---

## 🧭 Resumen del proyecto

Este proyecto implementa un **pipeline de datos end-to-end (ELT)** que captura posiciones de vuelo en tiempo real desde la **API de OpenSky Network**, las cruza con una base de referencia de aeronaves y estima el **consumo de combustible y las emisiones de CO₂ por hora de vuelo**, siguiendo una arquitectura de datos por capas (**Medallion: Bronze → Silver → Gold**).

El resultado se consume en un **dashboard de Power BI** que compara la eficiencia de emisiones entre **Airbus** y **Boeing**, desglosado por familia de avión (A320, A350, A380, 737, 747, 777, 787...) y con mapa geográfico del tráfico capturado.

El pipeline se ejecuta de forma **automática y diaria** mediante GitHub Actions, sin intervención manual.

---

## 🏗️ Arquitectura

<img width="1440" height="1240" alt="image" src="https://github.com/user-attachments/assets/92f05453-a8c2-4d68-aa59-be6028c2cd6c" />
**Orquestación:** GitHub Actions ejecuta el pipeline completo cada día a las 06:00 UTC (`cron`), levantando un contenedor efímero de PostgreSQL, aplicando el esquema SQL, corriendo el ETL en Python y publicando el CSV final de vuelta al repositorio.

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| **Ingesta** | Python (`requests`), API REST de OpenSky Network |
| **Almacenamiento** | PostgreSQL 16 (esquemas `bronze` / `silver` / `gold`) |
| **Transformación** | Python (`pandas`, `psycopg2`) |
| **Orquestación** | GitHub Actions (cron diario + ejecución manual) |
| **Infraestructura local** | Docker / Docker Compose |
| **Visualización** | Power BI |
| **Gestión de secretos** | `python-dotenv` + GitHub Secrets |

---

## 📂 Estructura del repositorio

| Ruta | Descripción |
|---|---|
| `.github/workflows/pipeline.yml` | Orquestación diaria (GitHub Actions) |
| `data/reference/` | `aircraftDatabase.csv`, descargado en cada ejecución |
| `data/gold/` | `flight_efficiency.csv`, salida publicada del pipeline |
| `sql/01_bronze.sql` | Esquema de la capa Bronze |
| `sql/02_silver.sql` | Esquema de la capa Silver |
| `sql/03_gold.sql` | Esquema de la capa Gold |
| `src/extract.py` | Llamada a la API de OpenSky |
| `src/load_bronze.py` | Ingesta cruda → Bronze |
| `src/transform_silver.py` | Limpieza + cruce con referencia → Silver |
| `src/transform_gold.py` | Cálculo de consumo/CO₂ → Gold |
| `docker-compose.yml` | PostgreSQL local para desarrollo |
| `requirements.txt` | Dependencias de Python |
| `.env` | Credenciales (no versionado) |

---

## ⚙️ Cómo funciona el pipeline

### 1️⃣ Extracción (`extract.py`)
Consulta el endpoint `/api/states/all` de OpenSky Network acotado a un **bounding box de Europa** (lat 35–60, lon -10–30), obteniendo posición, velocidad, altitud y callsign de todos los vuelos activos en ese momento.

### 2️⃣ Bronze (`load_bronze.py`)
Inserta el payload crudo de cada vuelo en `bronze.raw_flights`, conservando el JSON original (`raw_payload`) para trazabilidad completa además de las columnas ya tipadas.

### 3️⃣ Silver (`transform_silver.py`)
- Descarta registros sin coordenadas válidas.
- Cruza cada vuelo (`icao24`) con el **aircraft reference dataset oficial de OpenSky** para obtener fabricante y modelo.
- Clasifica cada aeronave como `Airbus`, `Boeing` u `Other`.
- Normaliza timestamps a `captured_at`.

### 4️⃣ Gold (`transform_gold.py`)
- Filtra solo aeronaves Airbus/Boeing.
- Aplica una tabla de **consumo de combustible por hora (kg/h) por familia de modelo**, basada en documentación pública de fabricantes y reportes operativos.
- Calcula `estimated_co2_kg_h = fuel_burn_kg_h × 3.16` (factor de conversión ICAO/IATA de kg CO₂ por kg de combustible quemado).
- Publica el resultado final en `gold.flight_efficiency`.

### 5️⃣ Publicación
El job de GitHub Actions exporta `gold.flight_efficiency` a CSV (`data/gold/flight_efficiency.csv`) y lo commitea automáticamente al repositorio, dejándolo listo para ser consumido por Power BI vía conexión a archivo o refresco programado.

---

## 🚀 Puesta en marcha local

### Requisitos previos
- Python 3.12+
- Docker y Docker Compose
- Cuenta gratuita en [OpenSky Network](https://opensky-network.org/) (usuario/contraseña de la API)

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Dguillenc/airbus-fleet-efficiency.git
cd airbus-fleet-efficiency

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

# 3. Configurar variables de entorno
# Crear un archivo .env en la raíz con:
#   DB_PASSWORD=tu_password
#   OPENSKY_USER=tu_usuario
#   OPENSKY_PASS=tu_password_opensky

# 4. Levantar PostgreSQL con el esquema Bronze/Silver/Gold ya inicializado
docker compose up -d

# 5. Descargar la base de referencia de aeronaves de OpenSky
curl -L -o data/reference/aircraftDatabase.csv https://opensky-network.org/datasets/metadata/aircraftDatabase.csv

# 6. Ejecutar el pipeline completo
python src/load_bronze.py
python src/transform_silver.py
python src/transform_gold.py
```

---

## 🔄 Automatización (GitHub Actions)

El workflow [`pipeline.yml`](.github/workflows/pipeline.yml):

- Se ejecuta **automáticamente cada día a las 06:00 UTC** y también de forma manual (`workflow_dispatch`).
- Levanta un servicio de PostgreSQL efímero como parte del job.
- Aplica el esquema SQL (`bronze` → `silver` → `gold`).
- Descarga la última versión del `aircraftDatabase.csv` de OpenSky.
- Ejecuta el ETL completo (`extract → bronze → silver → gold`).
- Exporta la tabla Gold a CSV y hace commit/push automático del resultado.

**Secrets requeridos en el repositorio de GitHub:**

| Secret | Descripción |
|---|---|
| `DB_PASSWORD` | Contraseña de PostgreSQL |
| `OPENSKY_USER` | Usuario de la API de OpenSky |
| `OPENSKY_PASS` | Contraseña de la API de OpenSky |

---

## 📈 Dashboard (Power BI)

El dashboard conecta contra `data/gold/flight_efficiency.csv` y muestra:

- **Emisiones de CO₂ estimadas (kg/h) por familia de avión**, comparando Airbus vs Boeing.
- **KPIs agregados**: CO₂ promedio, consumo de combustible promedio y número de aeronaves únicas (`icao24`) capturadas.
- **Mapa geográfico** con la densidad de tráfico aéreo detectado en el bounding box europeo.
- **Filtro por fabricante** para aislar la flota Airbus o Boeing.

> El CSV se actualiza a diario de forma automática, por lo que basta con configurar un refresco programado en Power BI (o reimportar el archivo) para mantener el dashboard al día.

---

## ⚠️ Metodología y limitaciones

- Los datos de posición provienen de **ADS-B en tiempo real** vía OpenSky Network, por lo que la cobertura depende de la densidad de receptores terrestres (mayor en Europa y Norteamérica).
- El **consumo de combustible por modelo** se basa en cifras públicas de fabricantes y reportes operativos de referencia; los valores marcados como estimados por interpolación entre modelos similares se documentan explícitamente en el propio código (`src/transform_gold.py`).
- El factor de **3,16 kg CO₂ por kg de combustible** corresponde al estándar de conversión utilizado por ICAO/IATA para combustible de aviación (Jet A-1).
- Este proyecto tiene fines **analíticos y de portfolio**; no sustituye cálculos oficiales de emisiones certificadas (p. ej. metodología ICAO CO₂ Certification).

---

## 🗺️ Próximos pasos

- [ ] Incorporar el dataset oficial de certificación de emisiones **ICAO CO₂** como validación cruzada de las estimaciones.
- [ ] Migrar transformaciones Silver/Gold a **dbt** para tests de calidad de datos y linaje documentado.
- [ ] Ampliar el bounding box a cobertura global por fases.
- [ ] Añadir capa de particionado histórico para análisis de tendencias temporales.

---

## 👤 Autor

**Daniel Guillén**
Técnico de mantenimiento electrónico/eléctrico (sistemas de defensa, Indra) en transición hacia Data Engineering & Analytics Engineering.

[GitHub](https://github.com/Dguillenc) · [LinkedIn](https://linkedin.com/in/danielgc97)

---

<div align="center">
<sub>Fuente de datos: OpenSky Network API · Factor de emisiones ICAO/IATA (3,16 kg CO₂ por kg de combustible) · Actualización diaria automatizada vía GitHub Actions</sub>
</div>
