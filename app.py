import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# === CONFIG ===
st.set_page_config(
    page_title="Dashboard Destinazioni",
    layout="wide",  # full-width layout
    initial_sidebar_state="expanded"
)

# === FUNZIONE: CARICAMENTO DATI ===
@st.cache_data
def load_data():
    sheet_url = "https://docs.google.com/spreadsheets/d/1Vq7n1KaJzm_14lMrtkgzS9lkBgZ-1ddIZiwkPO9r7zE/export?format=csv"
    df = pd.read_csv(sheet_url, parse_dates=["date"])
    return df

df = load_data()

# === SIDEBAR FILTRI ===
st.sidebar.header("🎛️ Filtri")

# Filtro data
df["date"] = pd.to_datetime(df["date"], errors="coerce")
min_date, max_date = df["date"].min().date(), df["date"].max().date()
start_date, end_date = st.sidebar.date_input("📅 Intervallo Date", (min_date, max_date),
                                             min_value=min_date, max_value=max_date)

# Filtro destinazioni dettagliate
details = df["detailDestinationName"].dropna().unique()
selected_details = st.sidebar.multiselect("📍 Destinazioni Dettagliate", sorted(details))

# Filtro ricerca testuale
search = st.sidebar.text_input("🔍 Cerca in 'description' o 'destinationName'")

# Ordinamento
sort_column = st.sidebar.selectbox("🔃 Ordina per", df.columns)
sort_order = st.sidebar.radio("Ordine", ["Crescente", "Decrescente"], horizontal=True)
ascending = sort_order == "Crescente"

# === FILTRAGGIO DATI ===
filtered_df = df.copy()
filtered_df = filtered_df[
    (filtered_df["date"].dt.date >= start_date) &
    (filtered_df["date"].dt.date <= end_date)
]

if selected_details:
    filtered_df = filtered_df[filtered_df["detailDestinationName"].isin(selected_details)]

if search:
    search_lower = search.lower()
    filtered_df = filtered_df[
        filtered_df["description"].str.lower().str.contains(search_lower, na=False) |
        filtered_df["destinationName"].str.lower().str.contains(search_lower, na=False)
    ]

filtered_df = filtered_df.sort_values(by=sort_column, ascending=ascending)

# === HEADER ===
st.title("📊 Dashboard delle Destinazioni")
st.markdown(f"Mostrando **{len(filtered_df)}** record filtrati su **{len(df)}** totali.")

# === GRAFICI ===
col1, col2 = st.columns(2)

with col1:
    if "detailDestinationName" in filtered_df.columns:
        chart1 = px.bar(
            filtered_df["detailDestinationName"].value_counts().reset_index(),
            x="index", y="detailDestinationName",
            labels={"index": "Destinazione", "detailDestinationName": "Numero"},
            title="📍 Distribuzione delle destinazioni"
        )
        st.plotly_chart(chart1, use_container_width=True)

with col2:
    if "date" in filtered_df.columns:
        chart2 = px.histogram(
            filtered_df, x="date",
            nbins=30,
            title="🕒 Numero di eventi per giorno"
        )
        st.plotly_chart(chart2, use_container_width=True)

# === IMPOSTAZIONI IMPAGINAZIONE ===
st.subheader("📄 Tabella dei dati")
page_size = 10
total_rows = filtered_df.shape[0]
total_pages = (total_rows - 1) // page_size + 1
page = st.number_input("Pagina", min_value=1, max_value=total_pages, value=1)

start_idx = (page - 1) * page_size
end_idx = start_idx + page_size

st.write(f"Mostrando righe **{start_idx + 1} - {min(end_idx, total_rows)}** su **{total_rows}**")
st.dataframe(filtered_df.iloc[start_idx:end_idx], use_container_width=True)

