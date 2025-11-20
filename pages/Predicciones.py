import streamlit as st
import pandas as pd
import numpy as np
import joblib
import duckdb
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Predicción por Colonia", layout="wide")

st.title("🔍 Predicción de Robos: Colonia por Hora")
st.markdown("Distribución del riesgo predicho desglosado por **Alcaldía, Colonia y Hora**.")

# ==========================================
# 1. CARGA DE DATOS HISTÓRICOS (Para saber el "DÓNDE")
# ==========================================
@st.cache_data
def load_historical_stats():
    try:
        # Conectamos a la misma BD que usa tu EDA.py
        con = duckdb.connect("crimes_fgj.db", read_only=True)
        
        # Filtramos solo transeúnte para calcular los pesos reales de cada zona
        query = """
            SELECT alcaldia_hecho, colonia_hecho, COUNT(*) as total_robos
            FROM crimes_raw
            WHERE delito ILIKE '%TRANSEUNTE%' 
            AND alcaldia_hecho IS NOT NULL 
            AND colonia_hecho IS NOT NULL
            GROUP BY alcaldia_hecho, colonia_hecho
        """
        df = con.execute(query).df()
        con.close()
        return df
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return pd.DataFrame()

df_stats = load_historical_stats()

# ==========================================
# 2. CARGA DEL MODELO (Para predecir el "CUÁNDO")
# ==========================================
@st.cache_resource
def load_model():
    try:
        return joblib.load('xgboost_model.pkl')
    except:
        return None

model = load_model()

# ==========================================
# 3. INTERFAZ DE USUARIO
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
    fecha_sel = st.date_input("Fecha a predecir", datetime.now())

with col2:
    if not df_stats.empty:
        alcaldias = sorted(df_stats['alcaldia_hecho'].unique())
        alcaldia_sel = st.selectbox("Selecciona Alcaldía", alcaldias)
    else:
        alcaldia_sel = None
        st.warning("No hay datos de alcaldías disponibles.")

with col3:
    top_n = st.slider("Mostrar Top N Colonias más peligrosas", 5, 50, 10)

# ==========================================
# 4. LÓGICA DE PREDICCIÓN
# ==========================================
if st.button("Generar Matriz de Predicción") and model and alcaldia_sel:
    
    # A) Obtener predicción temporal base (Curva de 24 horas)
    # -------------------------------------------------------
    input_data = []
    dia_sem = fecha_sel.weekday()
    
    # Features esperadas por tu modelo (según el error anterior)
    expected_features = ['año', 'mes', 'dia', 'hora', 'dia_semana', 
                         'sin_hora', 'cos_hora', 
                         'lag_1', 'lag_2', 'lag_3', 'lag_6', 'lag_12', 'lag_24']

    for h in range(24):
        sin_h = np.sin(2 * np.pi * h / 24)
        cos_h = np.cos(2 * np.pi * h / 24)
        
        row = {
            "año": fecha_sel.year, "mes": fecha_sel.month, "dia": fecha_sel.day,
            "hora": h, "dia_semana": dia_sem,
            "sin_hora": sin_h, "cos_hora": cos_h,
            # Rellenamos lags con 0 para proyección futura
            "lag_1": 0, "lag_2": 0, "lag_3": 0, "lag_6": 0, "lag_12": 0, "lag_24": 0
        }
        input_data.append(row)
    
    df_time_pred = pd.DataFrame(input_data)[expected_features]
    
    # Predicción base (Riesgo general en CDMX por hora)
    riesgo_base_horario = model.predict(df_time_pred)
    
    # B) Obtener pesos espaciales (Distribución por Colonia)
    # ------------------------------------------------------
    # Filtramos colonias de la alcaldía seleccionada
    df_local = df_stats[df_stats['alcaldia_hecho'] == alcaldia_sel].copy()
    
    # Calculamos el peso de cada colonia (frecuencia relativa)
    # Esto responde: "Si hay un robo, ¿qué tan probable es que sea en ESTA colonia?"
    total_crimes_local = df_local['total_robos'].sum()
    df_local['peso'] = df_local['total_robos'] / total_crimes_local
    
    # Nos quedamos con las Top N colonias para que el gráfico sea legible
    df_top_colonias = df_local.sort_values('total_robos', ascending=False).head(top_n)
    
    # C) Cruzar Datos: Matriz Colonia x Hora
    # ------------------------------------------------------
    matrix_data = {}
    
    # Iteramos por colonia
    for _, row_colonia in df_top_colonias.iterrows():
        colonia_name = row_colonia['colonia_hecho']
        peso_colonia = row_colonia['peso']
        
        # La predicción de la colonia es: (Riesgo Base Hora) * (Factor de la Colonia)
        # Nota: Multiplicamos por un factor para simular cantidad, ajusta según tu necesidad
        prediccion_colonia = riesgo_base_horario * peso_colonia * 100 
        matrix_data[colonia_name] = prediccion_colonia

    # Crear DataFrame final (Filas: Colonias, Columnas: Horas 0-23)
    df_heatmap = pd.DataFrame(matrix_data).T # Transponemos para que Colonias sean filas
    df_heatmap.columns = [f"{h}:00" for h in range(24)]
    
    # ==========================================
    # 5. VISUALIZACIÓN
    # ==========================================
    st.subheader(f"🔥 Mapa de Calor de Riesgo: {alcaldia_sel}")
    st.caption("La escala de color indica la intensidad predicha de robos.")
    
    # Ajuste del tamaño de la figura según cuántas colonias mostremos
    fig_height = max(6, top_n * 0.4)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    
    sns.heatmap(df_heatmap, cmap="inferno", annot=False, fmt=".2f", linewidths=.5, ax=ax)
    plt.xlabel("Hora del Día")
    plt.ylabel("Colonia")
    st.pyplot(fig)
    
    # Tabla de datos detallada
    with st.expander("Ver datos detallados en tabla"):
        st.dataframe(df_heatmap.style.background_gradient(cmap="Reds", axis=None))

elif not model:
    st.error("⚠️ No se encontró el modelo 'xgboost_model.pkl'.")
elif not alcaldia_sel:
    st.info("Esperando selección de alcaldía...")