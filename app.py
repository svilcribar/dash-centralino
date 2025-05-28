import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Funzione per caricare i dati da Google Sheets
@st.cache_data
def load_data():
    sheet_id = "1Vq7n1KaJzm_14lMrtkgzS9lkBgZ-1ddIZiwkPO9r7zE"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    # Colonne da interpretare come date
    date_columns = [
        "startTime", "answerTime", "endTime",
        "detailEnterTime", "detailAnswerTime", "detailExitTime"
    ]

    df = pd.read_csv(sheet_url, parse_dates=date_columns)
    return df

# Carica i dati
df = load_data()

# Filtro: intervallo di date
st.sidebar.header("🔍 Filtri")

min_date = df['startTime'].min().date()
max_date = df['startTime'].max().date()
start_date, end_date = st.sidebar.date_input("📅 Intervallo date", [min_date, max_date], min_value=min_date, max_value=max_date)

# Filtro: destinazione
destinations = df['detailDestinationName'].dropna().unique()
selected_destinations = st.sidebar.multiselect("🎯 Destinazioni", sorted(destinations), default=sorted(destinations))

# Applica i filtri
df = df[
    (df['startTime'].dt.date >= start_date) &
    (df['startTime'].dt.date <= end_date) &
    (df['detailDestinationName'].isin(selected_destinations))
]

# KPI: Percentuale utenti che richiamano dopo una NOTSERVED e ottengono SERVED
# Considera solo chiamate in ingresso (IN)
incoming_calls = df[df['direction'] == 'IN'].copy()

# Ordina per chiamante e tempo
incoming_calls.sort_values(by=['callerId', 'startTime'], inplace=True)

# Per ogni chiamante, troviamo se una NOTSERVED è seguita da una SERVED
results = []
seen_callers = set()

for caller, group in incoming_calls.groupby('callerId'):
    statuses = group['status'].tolist()
    if 'NOTSERVED' in statuses and 'SERVED' in statuses:
        results.append(1)
    else:
        results.append(0)

# KPI finale
percent_recall_success = 100 * sum(results) / len(results) if results else 0
st.metric("📈 % utenti che richiamano dopo NOTSERVED e ricevono risposta", f"{percent_recall_success:.1f}%")

# Aggiungi colonna con giorno della settimana
df['weekday'] = df['startTime'].dt.day_name()

# Conta chiamate per giorno
calls_per_weekday = df['weekday'].value_counts().reindex(
    ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
).fillna(0)

# Grafico
st.subheader("📅 Chiamate per giorno della settimana")
st.bar_chart(calls_per_weekday)

day_map = {
    'Monday': 'Lunedì', 'Tuesday': 'Martedì', 'Wednesday': 'Mercoledì',
    'Thursday': 'Giovedì', 'Friday': 'Venerdì', 'Saturday': 'Sabato', 'Sunday': 'Domenica'
}
df['weekday'] = df['startTime'].dt.day_name().map(day_map)

# Header
st.title("📊 Dashboard Centralino CRI")

# Statistiche principali
st.header("Statistiche principali")

total_calls = len(df)
answered_calls = df['status'].eq('SERVED').sum()
missed_calls = total_calls - answered_calls
unique_callers = df['callerId'].nunique()
total_conversation_sec = df['conversationTime'].sum()
total_conversation_hr = round(total_conversation_sec / 3600, 1)
avg_waiting_time_sec = round(df['waitingTime'].mean(), 1)

col1, col2, col3 = st.columns(3)
col1.metric("Totale chiamate", f"{total_calls:,}")
col2.metric("Risposte", f"{answered_calls:,}")
col3.metric("Non risposte", f"{missed_calls:,}")

col1, col2 = st.columns(2)
col1.metric("Chiamanti unici", f"{unique_callers:,}")
col2.metric("Ore di conversazione", f"{total_conversation_hr} h")

st.metric("⏱️ Attesa media", f"{avg_waiting_time_sec} s")

# Grafico chiamate per ora
st.subheader("📈 Chiamate per ora del giorno")
df['hour'] = df['startTime'].dt.hour
calls_by_hour = df.groupby('hour').size()
st.bar_chart(calls_by_hour)

# Grafico risposte vs non risposte
st.subheader("✅ Risposte vs ❌ Non risposte")
status_counts = df['status'].value_counts()
st.bar_chart(status_counts)

# Tempo medio di attesa per ora
st.subheader("⏱️ Tempo medio di attesa per ora")
wait_by_hour = df.groupby('hour')['waitingTime'].mean()
st.line_chart(wait_by_hour)

# Analisi dei richiamanti
st.subheader("🔁 Analisi dei richiamanti")
repeat_calls = df.groupby('callerId').size().reset_index(name='num_calls')
repeat_stats = repeat_calls['num_calls'].value_counts().sort_index()
st.bar_chart(repeat_stats)

# Analisi "tempo fino alla risposta"
st.subheader("⏳ Tempo medio fino alla risposta per richiamata")
answered_df = df[df['status'] == 'SERVED'].sort_values(by='startTime')
answered_df['prev_call_time'] = answered_df.groupby('callerId')['startTime'].shift(1)
answered_df['delta_to_answer'] = (answered_df['answerTime'] - answered_df['prev_call_time']).dt.total_seconds()
avg_delta = round(answered_df['delta_to_answer'].mean(skipna=True) / 60, 1)
st.metric("⏱️ Tempo medio tra tentativi fino a risposta", f"{avg_delta} minuti")

