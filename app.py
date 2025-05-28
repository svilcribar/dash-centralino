import pandas as pd
import streamlit as st
import plotly.express as px

# ---- CONFIGURAZIONE PAGINA ---- #
st.set_page_config(
    page_title="Dashboard Centralino",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- CARICAMENTO DATI ---- #
sheet_id = "1Vq7n1KaJzm_14lMrtkgzS9lkBgZ-1ddIZiwkPO9r7zE"
sheet_name = "Sheet1"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

@st.cache_data

def load_data():
    df = pd.read_csv(sheet_url, parse_dates=[
        "startTime", "endTime", "detailEnterTime", "detailAnswerTime", "detailExitTime"])
    return df

df = load_data()

# ---- SIDEBAR FILTRI ---- #
st.sidebar.header("Filtri")

# Filtro per data
min_date = df["startTime"].min().date()
max_date = df["startTime"].max().date()
date_range = st.sidebar.date_input("Intervallo data", [min_date, max_date])

if len(date_range) == 2:
    start_date, end_date = date_range
    df = df[(df["startTime"].dt.date >= start_date) & (df["startTime"].dt.date <= end_date)]

# Filtro per destinazione
all_dests = sorted(df["detailDestinationName"].dropna().unique())
selected_dests = st.sidebar.multiselect("Destinazioni", all_dests)

if selected_dests:
    df = df[df["detailDestinationName"].isin(selected_dests)]

# ---- METRICHE RIASSUNTIVE ---- #
st.title("📊 Dashboard Centralino")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Totale Chiamate", len(df))
with col2:
    st.metric("Tempo Totale Conversazione (s)", int(df["conversationTime"].sum()))
with col3:
    st.metric("Operatori Coinvolti", df["operator"].nunique())

# ---- GRAFICI ---- #
st.subheader("Chiamate per Destinazione")
calls_by_dest = df["detailDestinationName"].value_counts().reset_index()
calls_by_dest.columns = ["Destinazione", "Numero di chiamate"]
fig1 = px.bar(calls_by_dest, x="Destinazione", y="Numero di chiamate",
             color="Numero di chiamate", color_continuous_scale="Viridis")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("Chiamate per Giorno")
df["giorno"] = df["startTime"].dt.date
calls_by_day = df.groupby("giorno").size().reset_index(name="chiamate")
fig2 = px.line(calls_by_day, x="giorno", y="chiamate", markers=True)
st.plotly_chart(fig2, use_container_width=True)

st.caption("Dati caricati da Google Sheets | Aggiornamento in tempo reale")
