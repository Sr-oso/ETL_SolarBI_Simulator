import os
import pandas as pd
from sqlalchemy import create_engine, text

# Credenciales de conexión a PostgreSQL
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "solarbi_db")

# Crear el motor de conexión
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def ejecutar_etl():
    path_bronze = "data/bronze/telemetria.csv"
    if not os.path.exists(path_bronze):
        raise FileNotFoundError("Primero debes ejecutar: python etl/simulador.py")

    df_raw = pd.read_csv(path_bronze)
    total_leidas = len(df_raw)

    df_raw["ts"] = pd.to_datetime(df_raw["ts"])
    df_raw["p_ac_kw"] = pd.to_numeric(df_raw["p_ac_kw"], errors="coerce")
    df_raw["irradiancia_wm2"] = pd.to_numeric(df_raw["irradiancia_wm2"], errors="coerce")

    # 1. Aplica Reglas de Calidad (Silver)
    df_no_dup = df_raw.drop_duplicates(subset=["ts", "dispositivo_id"])
    rechazados_dup = total_leidas - len(df_no_dup)

    df_rango = df_no_dup[df_no_dup["p_ac_kw"] >= 0]
    rechazados_rango = len(df_no_dup) - len(df_rango)

    df_valido = df_rango.dropna(subset=["irradiancia_wm2"]).copy()
    rechazados_nulos = len(df_rango) - len(df_valido)

    total_validas = len(df_valido)
    pct_validos = round((total_validas / total_leidas) * 100, 2) if total_leidas > 0 else 0.0

    print("   REPORTE SILVER   ")
    print(f"Filas leídas (Bronze)        : {total_leidas}")
    print(f"Rechazadas por Duplicados    : {rechazados_dup}")
    print(f"Rechazadas por Rango (<0 kW) : {rechazados_rango}")
    print(f"Rechazadas por Nulos         : {rechazados_nulos}")
    print(f"Filas Válidas (Silver)       : {total_validas}")
    print(f"Porcentaje Datos Válidos     : {pct_validos}%")

    # Guardar copia local en Silver
    os.makedirs("data/silver", exist_ok=True)
    df_valido.to_csv("data/silver/telemetria_limpia.csv", index=False)

    # 2. Carga a PostgreSQL (Silver)
    with engine.begin() as conn:
        for _, row in df_valido.iterrows():
            query_silver = text("""
                INSERT INTO silver.lectura_5min (ts, dispositivo_id, p_ac_kw, irradiancia_wm2, temp_modulo_c)
                VALUES (:ts, :dispositivo_id, :p_ac_kw, :irradiancia_wm2, :temp_modulo_c)
                ON CONFLICT (ts, dispositivo_id) DO UPDATE SET
                    p_ac_kw = EXCLUDED.p_ac_kw,
                    irradiancia_wm2 = EXCLUDED.irradiancia_wm2,
                    temp_modulo_c = EXCLUDED.temp_modulo_c;
            """)
            conn.execute(query_silver, {
                "ts": row["ts"],
                "dispositivo_id": int(row["dispositivo_id"]),
                "p_ac_kw": float(row["p_ac_kw"]),
                "irradiancia_wm2": float(row["irradiancia_wm2"]),
                "temp_modulo_c": float(row["temp_modulo_c"])
            })

    # 3. Transformación y Carga a Gold (dwh.fact_energia_dia)
    df_valido["energia_intervalo_kwh"] = df_valido["p_ac_kw"] * (5 / 60)
    df_valido["fecha"] = df_valido["ts"].dt.date

    df_gold = df_valido.groupby(["fecha", "dispositivo_id"]).agg(
        energia_kwh=("energia_intervalo_kwh", "sum")
    ).reset_index()
    df_gold["pct_datos_validos"] = pct_validos

    with engine.begin() as conn:
        for _, row in df_gold.iterrows():
            query_gold = text("""
                INSERT INTO dwh.fact_energia_dia (fecha, dispositivo_id, energia_kwh, pct_datos_validos)
                VALUES (:fecha, :dispositivo_id, :energia_kwh, :pct_datos_validos)
                ON CONFLICT (fecha, dispositivo_id) DO UPDATE SET
                    energia_kwh = EXCLUDED.energia_kwh,
                    pct_datos_validos = EXCLUDED.pct_datos_validos;
            """)
            conn.execute(query_gold, {
                "fecha": row["fecha"],
                "dispositivo_id": int(row["dispositivo_id"]),
                "energia_kwh": float(round(row["energia_kwh"], 3)),
                "pct_datos_validos": float(row["pct_datos_validos"])
            })

    print("Carga idempotente a PostgreSQL finalizada exitosamente.")

if __name__ == "__main__":
    ejecutar_etl()