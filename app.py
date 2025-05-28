import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard Centralino", layout="wide")

@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQEZKp2LMZ2uwMGgfvRDGuz8UeTVGscXGBt2UoQxBhBDdOqZ-fGWB23fqZCr5vRUTcYYbDgfXZGP1hN/pub?output=csv"
    df = pd.read_csv(url, parse_dates=["startTime", "answerTime", "endTime", "detailEnterTime", "detailAnswerTime", "detailExitTime"])
    return df

df = load_data()

# FILTRI
st.sidebar.title("Filtri")
data_min, data_max = df["startTime"].min(), df["startTime"].max()
intervallo_date = st.sidebar.date_input("Intervallo date", [data_min.date(), data_max.date()])

status = st.sidebar.multiselect("Status", options=df["status"].unique(), default=list(df["status"].unique()))
dest = st.sidebar.multiselect("Destinazione", options=df["detailDestinationName"].dropna().unique(), default=list(df["detailDestinationName"].dropna().unique()))

filtri = (
    (df["startTime"].dt.date >= intervallo_date[0]) &
    (df["startTime"].dt.date <= intervallo_date[1]) &
    (df["status"].isin(status)) &
    (df["detailDestinationName"].isin(dest))
)
df_filt = df[filtri]

# STATISTICHE
st.title("📞 Dashboard Chiamate Centralino")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Totale chiamate", len(df_filt))
col2.metric("Chiamate risposte", (df_filt["status"] == "SERVED").sum())
col3.metric("Chiamate non risposte", (df_filt["status"] != "SERVED").sum())
col4.metric("Chiamanti unici", df_filt["callerId"].nunique())

tempo_conv_sec = df_filt["conversationTime"].sum()
tempo_conv_ore = round(tempo_conv_sec / 3600, 1)
tempo_att_medio = round(df_filt["waitingTime"].mean(), 1)

col5, col6 = st.columns(2)
col5.metric("🕒 Tempo totale di conversazione", f"{tempo_conv_ore} h")
col6.metric("⏱️ Tempo medio di attesa", f"{tempo_att_medio} sec")

# GRAFICI
st.subheader("📊 Andamento delle chiamate")
df_filt["ora"] = df_filt["startTime"].dt.hour

fig1 = px.histogram(df_filt, x="ora", title="Numero di chiamate per ora", nbins=24)
fig2 = px.pie(df_filt, names="status", title="Distribuzione Risposte vs Non Risposte")

attesa_ora = df_filt.groupby("ora")["waitingTime"].mean().reset_index()
fig3 = px.line(attesa_ora, x="ora", y="waitingTime", title="Tempo medio di attesa per ora")

st.plotly_chart(fig1, use_container_width=True)
st.plotly_chart(fig2, use_container_width=True)
st.plotly_chart(fig3, use_container_width=True)

# 🔁 ANALISI RICHIAMANTI
st.subheader("🔁 Analisi dei Richiamanti")
richiami = df_filt.sort_values("startTime").groupby("callerId")["startTime"].apply(list)
tempi_richiamo = richiami.apply(lambda x: [(x[i+1] - x[i]).total_seconds() for i in range(len(x)-1)] if len(x) > 1 else []).explode().dropna()

media_richiamo_sec = round(tempi_richiamo.mean(), 1)
col7, col8 = st.columns(2)
col7.metric("Richiamanti multipli", (richiami.apply(len) > 1).sum())
col8.metric("⏱️ Tempo medio tra richiami", f"{media_richiamo_sec} sec")

# 🔽 TABELLA
st.subheader("📋 Dati filtrati")
st.dataframe(df_filt.head(100))

st.download_button("📥 Scarica CSV", df_filt.to_csv(index=False).encode("utf-8"), file_name="chiamate_filtrate.csv")
