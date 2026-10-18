# SolarBI Simulator - Monitoreo y Gestión Energética de Plantas Solares   

---

## Integrantes del Equipo

By: Emmanuel Villa Peláez — `@Sr-oso`

---

## Descripción del Proyecto

SolarBI es una solución integral para el monitoreo en tiempo real y el análisis ejecutivo de plantas fotovoltaicas. La plataforma realiza la ingesta automatizada de telemetría (potencia AC e irradiancia), limpia los datos en una capa *Silver* en PostgreSQL, consolida indicadores agregados en una capa *Gold* (`dwh`) e integra la visualización mediante **Grafana** (monitoreo operativo) y **Power BI** (análisis gerencial de SLA y ahorro en COP).

---

## Pasos para la ejecución

### 1. Requisitos Previos
* **PostgreSQL 14+** instalado y ejecutándose en el puerto local predeterminado (`5432`).
* **Python 3.10+** configurado en el sistema con entorno de ejecución.
* **Grafana Server** activo localmente.
* **Power BI Desktop** instalado.

---

### 2. Configuración de la Base de Datos en PostgreSQL

1. Abre la consola interactiva de PostgreSQL (`psql`) o tu cliente SQL preferido (pgAdmin / DBeaver).
2. Ejecuta la inicialización de la base de datos y la capa *Silver*:
   ```bash
   psql -U postgres -f sql/01_init_db.sql

Esto creará la base de datos solarbi_db, el esquema silver y la tabla silver.lectura_5min con sus llaves compuestas.

3. Construye el esquema de la capa Gold con:
psql -U postgres -d solarbi_db -f sql/02_dwh_gold.sql

4. En la raíz del proyecto, crea un archivo de variables de entorno llamado .env con la siguiente estructura y tus credenciales locales:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=solarbi_db
DB_USER=postgres
DB_PASSWORD=Contraseña

5. Instala las dependencias de Python requeridas:
pip install pandas psycopg2-binary python-dotenv

6. Ejecuta el pipeline de extracción, limpieza e ingesta de datos:
python etl/run_etl.py

Nota de Idempotencia: El script puede ejecutarse múltiples veces consecutivas sobre la misma base de datos sin duplicar registros ni lanzar errores de clave duplicada (mantiene de forma estable los 841 registros en Silver).

Carga de datos en grafana:
1. Inicia sesión en tu servidor local de Grafana (http://localhost:3000).
2. Ve al menú lateral - Dashboards - New - Import.
3. Carga el archivo grafana/dashboard.json guardado en este repositorio.
4. Selecciona tu fuente de datos PostgreSQL de la lista y presiona Import.
5. Asegúrate de ajustar el rango temporal superior entre 05/10/2026 y 07/10/2026 para visualizar el panel de Series de Tiempo y el Gauge de SLA (94.6%).

CARGA DE DATOS POWERBI:
1. Abre el proyecto powerbi/SolarBI.pbix en Power BI Desktop.
2. Si te solicita actualización de credenciales, ingresa las de tu instancia local de PostgreSQL para conectar a la base solarbi_db.
3. Haz clic en Transformar datos - Configuración de origen de datos si requieres cambiar el servidor o puerto.

Arquitectura e implementación completa del proyecto: diseño de esquemas PostgreSQL (silver y dwh), desarrollo del pipeline ETL en Python (run_etl.py), pruebas de idempotencia, tablero completo en Grafana (Series de Tiempo, Gauge SLA y variables) y modelo en Power BI.
