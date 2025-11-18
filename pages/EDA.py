import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st
import pandas as pd
import folium                      
from folium.plugins import HeatMap, HeatMapWithTime, MarkerCluster
import numpy as np
import osmnx as ox
import branca.colormap as cm
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency
import squarify 
import duckdb   # 👈 agregado


# ===========================
# CONFIGURACIÓN DE LA PÁGINA
# ===========================
st.title("📊 Análisis Estadístico Descriptivo")
st.markdown("""
Esta página muestra un resumen del análisis descriptivo y las pruebas **Chi-cuadrado** 
realizadas con los datos de robos por alcaldía y horario.

**Hipótesis:**           
Ho: Central alcaldías do not record more robbery incidents during work hours (8 a.m.–6 p.m.), while peripheral alcaldías concentrate incidents at night.

Ha: Central alcaldías record more robbery incidents during work hours (8 a.m.–6 p.m.), while peripheral alcaldías concentrate incidents at night.
""")


# ===========================
# CARGA DE DATOS (CORREGIDA)
# ===========================
@st.cache_data
def load_data():
    file_path = "carpetasFGJ_acumulado_2025_01 (1).csv"

    query = f"""
        SELECT *
        FROM read_csv_auto(
            '{file_path}',
            header = TRUE,
            all_varchar = TRUE,  -- 👈 evita errores como NaT:00
            sample_size = -1
        )
    """

    df = duckdb.query(query).to_df()
    return df


df = load_data()


# ===========================
# LIMPIEZA BÁSICA
# ===========================
st.subheader("1️⃣ Limpieza de Datos")

st.write("Vista previa de los datos:")
st.dataframe(df.head())


# --- Filtrar sólo delitos de robo ---
df_robo = df[df['delito'].str.contains("ROBO", case=False, na=False)].copy()


# ===========================
# PARSE DE FECHAS Y HORAS (ROBUSTO)
# ===========================

# Convertir fecha_hecho a datetime
df_robo['fecha_hecho'] = pd.to_datetime(df_robo['fecha_hecho'], errors='coerce')

# Extraer hora de hora_hecho (limpia valores raros)
def parse_hora(valor):
    try:
        if isinstance(valor, str):
            h = pd.to_datetime(valor, errors='coerce')
            if pd.isna(h):
                return None
            return h.hour
        return None
    except:
        return None

df_robo['hora'] = df_robo['hora_hecho'].apply(parse_hora)

# Clasificación por horario
df_robo['horario'] = pd.cut(
    df_robo['hora'],
    bins=[0, 6, 12, 18, 24],
    labels=["Madrugada", "Mañana", "Tarde", "Noche"],
    right=False
)


# ===========================
# Selector de visualización
# ===========================
st.subheader("Visualización de robos por alcaldía")

opcion_viz = st.selectbox(
    "Seleccione el tipo de visualización:",
    ["Barras horizontales", "Heatmap", "Treemap"]
)


# ===========================
# Agrupar datos
# ===========================
conteo_alcaldia = df_robo['alcaldia_hecho'].value_counts().reset_index()
conteo_alcaldia.columns = ['alcaldía', 'robos']


# ===========================
# Visualización seleccionada
# ===========================

# ---------- 1. BARRAS HORIZONTALES ----------
if opcion_viz == "Barras horizontales":
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(
        data=conteo_alcaldia,
        y='alcaldía',
        x='robos',
        ax=ax
    )
    ax.set_title("Robos por alcaldía")
    ax.set_xlabel("Cantidad de robos")
    ax.set_ylabel("Alcaldía")
    st.pyplot(fig)


# ---------- 2. HEATMAP ----------
elif opcion_viz == "Heatmap":
    st.markdown("### Heatmap de robos por alcaldía")

    df_heat = conteo_alcaldia.pivot_table(
        index="alcaldía",
        values="robos",
        aggfunc="sum"
    )

    fig, ax = plt.subplots(figsize=(6, 10))
    sns.heatmap(df_heat, annot=True, fmt="d", cmap="Reds", ax=ax)
    ax.set_title("Heatmap de robos por alcaldía")
    st.pyplot(fig)


# ---------- 3. TREEMAP ----------
elif opcion_viz == "Treemap":
    st.markdown("### Treemap de robos por alcaldía")

    fig, ax = plt.subplots(figsize=(12, 8))
    
    squarify.plot(
        sizes=conteo_alcaldia['robos'],
        label=conteo_alcaldia['alcaldía'] + "\n" + conteo_alcaldia['robos'].astype(str),
        alpha=0.8
    )
    plt.axis('off')
    st.pyplot(fig)



# ===========================
# DISTRIBUCIÓN DE ROBOS POR HORA
# ===========================
st.subheader("3️⃣ Distribución de robos por hora del día (0–23 hrs)")

st.write("Ejemplo de horas convertidas correctamente:")
st.dataframe(df_robo[['hora_hecho', 'hora']].head(10))


alcaldias = ["Todas"] + sorted(df_robo['alcaldia_hecho'].dropna().unique().tolist())
selected_alcaldia = st.selectbox("Selecciona una alcaldía para filtrar:", alcaldias)

df_filtrado = df_robo.copy()
if selected_alcaldia != "Todas":
    df_filtrado = df_filtrado[df_filtrado['alcaldia_hecho'] == selected_alcaldia]

df_filtrado = df_filtrado[df_filtrado['hora'].between(0, 23, inclusive='both')]

fig, ax = plt.subplots(figsize=(10, 5))
sns.countplot(x="hora", data=df_filtrado, ax=ax)
ax.set_title(f"Distribución de robos por hora del día ({selected_alcaldia})")
ax.set_xlabel("Hora del día (0–23)")
ax.set_ylabel("Número de robos")
st.pyplot(fig)



# ===========================
# 4️⃣ TEST CHI-CUADRADO
# ===========================
st.subheader("4️⃣ Test Chi-cuadrada basado en la hipótesis (con filtro por radio)")

radio = st.slider("Radio para alcaldías centrales:", 8, 12, 10, 2, format="%d km")


if radio == 10:
    central_alcaldias = [
        "CUAUHTEMOC", "VENUSTIANO CARRANZA", "IZTACALCO",
        "BENITO JUAREZ", "MIGUEL HIDALGO", "GUSTAVO A. MADERO",
        "AZCAPOTZALCO", "COYOACAN"
    ]
    peripheral_alcaldias = [
        "ALVARO OBREGON", "IZTAPALAPA", "TLALPAN", "XOCHIMILCO",
        "MAGDALENA CONTRERAS", "CUAJIMALPA DE MORELOS",
        "TLAHUAC", "MILPA ALTA"
    ]

if radio == 8:
    central_alcaldias = [
        "CUAUHTEMOC", "VENUSTIANO CARRANZA", "IZTACALCO",
        "BENITO JUAREZ", "MIGUEL HIDALGO", "GUSTAVO A. MADERO"
    ]
    peripheral_alcaldias = [
        "AZCAPOTZALCO", "COYOACAN", "ALVARO OBREGON", "IZTAPALAPA",
        "TLALPAN", "XOCHIMILCO", "MAGDALENA CONTRERAS",
        "CUAJIMALPA DE MORELOS", "TLAHUAC", "MILPA ALTA"
    ]

if radio == 12:
    central_alcaldias = [
        "CUAUHTEMOC", "VENUSTIANO CARRANZA", "IZTACALCO",
        "BENITO JUAREZ", "MIGUEL HIDALGO", "GUSTAVO A. MADERO",
        "AZCAPOTZALCO", "COYOACAN", "ALVARO OBREGON", "IZTAPALAPA"
    ]
    peripheral_alcaldias = [
        "TLALPAN", "XOCHIMILCO", "MAGDALENA CONTRERAS",
        "CUAJIMALPA DE MORELOS", "TLAHUAC", "MILPA ALTA"
    ]


df_robo["alcaldia_hecho"] = df_robo["alcaldia_hecho"].str.upper().str.strip()

df_robo["zona"] = df_robo["alcaldia_hecho"].apply(
    lambda x: "Central" if x in central_alcaldias else
              "Periferica" if x in peripheral_alcaldias else "Otra"
)

df_test = df_robo[df_robo["zona"].isin(["Central", "Periferica"])].copy()

df_test["periodo"] = df_test["hora"].apply(
    lambda h: "Laboral" if h is not None and 8 <= h < 18 else "Noche"
)

contingency = pd.crosstab(df_test["zona"], df_test["periodo"])

st.markdown("### 📊 Tabla de contingencia")
st.dataframe(contingency)

chi2, p, dof, expected = chi2_contingency(contingency)

st.markdown(f"""
### 🔍 Resultados del test Chi²

- **Chi²:** `{chi2:.2f}`
- **p-valor:** `{p:.5f}`
- **Grados de libertad:** `{dof}`
""")


if p < 0.05:
    st.success("✅ Se rechaza H₀: Existe evidencia estadística para la hipótesis.")
else:
    st.warning("❌ No se rechaza H₀: No hay evidencia suficiente.")


fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(contingency, annot=True, fmt="d", cmap="YlGnBu", ax=ax)
ax.set_title("Frecuencia de robos por alcaldía y horario")
st.pyplot(fig)
