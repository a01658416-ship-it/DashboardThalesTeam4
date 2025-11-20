import streamlit as st
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import squarify
from scipy.stats import chi2_contingency

# ===========================
# CONFIGURACIÓN DE LA PÁGINA
# ===========================
st.title("📊 Análisis Estadístico Descriptivo")
st.markdown("""
Esta página muestra un resumen del análisis descriptivo y las pruebas **Chi-cuadrado** 
realizadas con los datos de robos por alcaldía y horario.

**Hipótesis:**           
Ho: Las alcaldías centrales NO registran más robos en horario laboral comparado con las periféricas.

Ha: Las alcaldías centrales registran más robos en horario laboral.
""")


# ===========================
# CARGA DESDE DUCKDB
# ===========================
@st.cache_data
def load_data():
    con = duckdb.connect("crimes_fgj.db", read_only=True)

    query = """
        SELECT *
        FROM crimes_raw
        WHERE delito ILIKE '%ROBO%'
    """

    df = con.execute(query).df()
    return df


df_robo = load_data()


# ===========================
# LIMPIEZA BÁSICA
# ===========================
st.subheader("1️⃣ Vista previa del dataset")
st.dataframe(df_robo.head())


# ===========================
# PARSE FECHA Y HORA
# ===========================
df_robo["fecha_hecho"] = pd.to_datetime(df_robo["fecha_hecho"], errors="coerce")
df_robo["hora"] = pd.to_datetime(df_robo["hora_hecho"], errors="coerce").dt.hour

df_robo["horario"] = pd.cut(
    df_robo["hora"],
    bins=[0, 6, 12, 18, 24],
    labels=["Madrugada", "Mañana", "Tarde", "Noche"],
    right=False
)

df_robo["alcaldia_hecho"] = df_robo["alcaldia_hecho"].str.upper().str.strip()


# ===========================
# QUERIES PARA AGRUPACIONES
# ===========================
con = duckdb.connect("crimes_fgj.db", read_only=True)

df_alcaldia = con.execute("""
    SELECT alcaldia_hecho AS alcaldia, COUNT(*) AS robos
    FROM crimes_raw
    WHERE delito ILIKE '%ROBO%'
    GROUP BY alcaldia_hecho
    ORDER BY robos DESC
""").df()


# ===========================
# Selector de visualización
# ===========================
st.subheader("2️⃣ Visualización de robos por alcaldía")

opcion_viz = st.selectbox(
    "Seleccione el tipo de visualización:",
    ["Barras horizontales", "Heatmap", "Treemap"]
)


# ---------- 1. BARRAS ----------
if opcion_viz == "Barras horizontales":
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(data=df_alcaldia, y="alcaldia", x="robos", ax=ax)
    ax.set_title("Robos por alcaldía")
    st.pyplot(fig)


# ---------- 2. HEATMAP ----------
elif opcion_viz == "Heatmap":
    df_heat = df_alcaldia.pivot_table(index="alcaldia", values="robos")
    fig, ax = plt.subplots(figsize=(6, 10))
    sns.heatmap(df_heat, annot=True, fmt="d", cmap="Reds", ax=ax)
    ax.set_title("Heatmap de robos por alcaldía")
    st.pyplot(fig)


# ---------- 3. TREEMAP ----------
elif opcion_viz == "Treemap":
    fig, ax = plt.subplots(figsize=(12, 8))
    squarify.plot(
        sizes=df_alcaldia["robos"],
        label=df_alcaldia["alcaldia"] + "\n" + df_alcaldia["robos"].astype(str),
        alpha=0.8
    )
    plt.axis("off")
    st.pyplot(fig)



# ===========================
# DISTRIBUCIÓN POR HORA
# ===========================
st.subheader("3️⃣ Distribución de robos por hora del día")

alcaldias = ["Todas"] + sorted(df_robo["alcaldia_hecho"].dropna().unique())
selected_alcaldia = st.selectbox("Filtrar por alcaldía:", alcaldias)

df_filtrado = df_robo if selected_alcaldia == "Todas" else df_robo[df_robo["alcaldia_hecho"] == selected_alcaldia]

df_filtrado = df_filtrado[df_filtrado["hora"].between(0, 23)]

fig, ax = plt.subplots(figsize=(10, 5))
sns.countplot(x="hora", data=df_filtrado, ax=ax)
ax.set_title(f"Robos por hora del día ({selected_alcaldia})")
st.pyplot(fig)



# ===========================
# TEST CHI-CUADRADO
# ===========================
st.subheader("4️⃣ Test Chi-cuadrado por zona (central vs periférica)")

radio = st.slider("Radio para alcaldías centrales:", 8, 12, 10)


# Definición de zonas según radio
zonas = {
    10: {
        "central": ["CUAUHTEMOC", "VENUSTIANO CARRANZA", "IZTACALCO", "BENITO JUAREZ", "MIGUEL HIDALGO", "GAM", "AZCAPOTZALCO", "COYOACAN"],
        "periferica": ["ALVARO OBREGON", "IZTAPALAPA", "TLALPAN", "XOCHIMILCO", "MAGDALENA CONTRERAS", "CUAJIMALPA DE MORELOS", "TLAHUAC", "MILPA ALTA"]
    },
    8: {
        "central": ["CUAUHTEMOC", "VENUSTIANO CARRANZA", "IZTACALCO", "BENITO JUAREZ", "MIGUEL HIDALGO", "GAM"],
        "periferica": ["AZCAPOTZALCO", "COYOACAN", "ALVARO OBREGON", "IZTAPALAPA", "TLALPAN", "XOCHIMILCO", "MAGDALENA CONTRERAS", "CUAJIMALPA DE MORELOS", "TLAHUAC", "MILPA ALTA"]
    },
    12: {
        "central": ["CUAUHTEMOC", "VENUSTIANO CARRANZA", "IZTACALCO", "BENITO JUAREZ", "MIGUEL HIDALGO", "GAM", "AZCAPOTZALCO", "COYOACAN", "ALVARO OBREGON", "IZTAPALAPA"],
        "periferica": ["TLALPAN", "XOCHIMILCO", "MAGDALENA CONTRERAS", "CUAJIMALPA DE MORELOS", "TLAHUAC", "MILPA ALTA"]
    }
}

central = zonas[radio]["central"]
periferica = zonas[radio]["periferica"]

df_robo["zona"] = df_robo["alcaldia_hecho"].apply(
    lambda x: "Central" if x in central else ("Periferica" if x in periferica else "Otra")
)

df_test = df_robo[df_robo["zona"].isin(["Central", "Periferica"])].copy()

df_test["periodo"] = df_test["hora"].apply(lambda h: "Laboral" if h is not None and 8 <= h < 18 else "Noche")

contingency = pd.crosstab(df_test["zona"], df_test["periodo"])
st.dataframe(contingency)

chi2, p, dof, expected = chi2_contingency(contingency)

st.markdown(f"""
### 🔍 Resultados Chi²  
- **Chi²:** `{chi2:.2f}`  
- **p-valor:** `{p:.5f}`  
- **Grados de libertad:** `{dof}`
""")

fig, ax = plt.subplots(figsize=(8, 5))
sns.heatmap(contingency, annot=True, fmt="d", cmap="YlGnBu", ax=ax)
st.pyplot(fig)
