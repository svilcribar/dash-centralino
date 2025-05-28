import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Funzione per caricare i dati da Google Sheets
@st.cache_data
def load_data():
    sheet_id = "1Vq7n1KaJzm_14lMrtkgzS9lkBgZ-1ddIZiwkPO9r7zE"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    date_columns = ["startTime", "answerTime", "endTime", "detailEnterTime", "detailAnswerTime", "detailExitTime"]
    df = pd.read_csv(sheet_url, parse_dates=date_columns)
    return df

df = load_data()

# ------------------------ FILTRI ------------------------
st.sidebar.header("🔍 Filtri")

min_date = df['startTime'].min().date()
max_date = df['startTime'].max().date()
start_date, end_date = st.sidebar.date_input("📅 Intervallo date", [min_date, max_date], min_value=min_date, max_value=max_date)

destinations = df['detailDestinationName'].dropna().unique()
selected_destinations = st.sidebar.multiselect("🎯 Destinazioni", sorted(destinations), default=sorted(destinations))

df = df[
    (df['startTime'].dt.date >= start_date) &
    (df['startTime'].dt.date <= end_date) &
    (df['detailDestinationName'].isin(selected_destinations))
]

# Escludi callerId con più di 30 chiamate in un mese
df['year_month'] = df['startTime'].dt.to_period('M')
monthly_counts = df.groupby(['callerId', 'year_month']).size().reset_index(name='calls')
excessive_callers = monthly_counts[monthly_counts['calls'] > 30]['callerId'].unique()
df = df[~df['callerId'].isin(excessive_callers)]

# Giorni e ore
day_map = {'Monday': 'Lunedì', 'Tuesday': 'Martedì', 'Wednesday': 'Mercoledì', 'Thursday': 'Giovedì', 'Friday': 'Venerdì', 'Saturday': 'Sabato', 'Sunday': 'Domenica'}
ordered_days = list(day_map.values())

df['weekday'] = pd.Categorical(df['startTime'].dt.day_name().map(day_map), categories=ordered_days, ordered=True)
df['hour'] = df['startTime'].dt.hour

# ------------------------ HEADER ------------------------
st.title("📊 Dashboard Centralino CRI")

# ------------------------ METRICHE GENERALI ------------------------
st.header("📞 Metriche generali")

total_calls = len(df)
answered_calls = df['status'].eq('SERVED').sum()
missed_calls = total_calls - answered_calls
unique_callers = df['callerId'].nunique()
total_conversation_hr = round(df['conversationTime'].sum() / 3600, 2)
avg_waiting_time_min = round(df['waitingTime'].mean() / 60, 1)

col1, col2, col3 = st.columns(3)
col1.metric("Totale chiamate", f"{total_calls:,}")
col2.metric("Risposte", f"{answered_calls:,}")
col3.metric("Non risposte", f"{missed_calls:,}")

col4, col5 = st.columns(2)
col4.metric("Chiamanti unici", f"{unique_callers:,}")
col5.metric("Minuti totali conversazione", f"{total_conversation_hr} h")

st.metric("⏱️ Attesa media", f"{avg_waiting_time_min} min")

# ------------------------ TEMPI E DURATE ------------------------
st.header("⏱️ Tempi e Durate")

response_rate = 100 * answered_calls / total_calls if total_calls else 0
st.metric("📈 Tasso di risposta", f"{response_rate:.1f}%")

avg_answer_time = (df[df['status'] == 'SERVED']['answerTime'] - df[df['status'] == 'SERVED']['startTime']).dt.total_seconds().mean()
if not np.isnan(avg_answer_time):
    st.metric("🕐 Tempo medio alla risposta", f"{round(avg_answer_time / 60, 1)} min")

avg_conversation_time = df[df['status'] == 'SERVED']['conversationTime'].mean()
if not np.isnan(avg_conversation_time):
    st.metric("🗣️ Durata media conversazione", f"{round(avg_conversation_time / 60, 1)} min")

# ------------------------ RICHIAMANTI E CLIENTI PERSI ------------------------
st.header("🔁 Richiamanti vs Clienti persi")

incoming_calls = df[df['direction'] == 'IN'].copy().sort_values(by=['callerId', 'startTime'])

first_nots = incoming_calls[incoming_calls['status'] == 'NOTSERVED'].sort_values('startTime')
first_nots = first_nots.groupby('callerId').first().reset_index()

richiamanti = 0
persi = 0

for _, row in first_nots.iterrows():
    caller = row['callerId']
    nots_time = row['startTime']
    future_calls = incoming_calls[(incoming_calls['callerId'] == caller) & (incoming_calls['startTime'] > nots_time)]
    within_48h = future_calls[(future_calls['startTime'] <= nots_time + pd.Timedelta(hours=48)) & (future_calls['status'] == 'SERVED')]
    if not within_48h.empty:
        richiamanti += 1
        continue
    within_7d = future_calls[future_calls['startTime'] <= nots_time + pd.Timedelta(days=7)]
    if within_7d.empty:
        persi += 1

total_nots = len(first_nots)
percent_richiamanti = 100 * richiamanti / total_nots if total_nots else 0
percent_persi = 100 * persi / total_nots if total_nots else 0

st.metric("🔁 Richiamanti entro 48h", f"{percent_richiamanti:.1f}% ({richiamanti})")
st.metric("🚫 Clienti persi (>7gg)", f"{percent_persi:.1f}% ({persi})")

# ------------------------ DISTRIBUZIONI TEMPORALI ------------------------
st.header("📆 Distribuzione chiamate")

st.subheader("Chiamate per giorno della settimana")
calls_per_weekday = df['weekday'].value_counts().sort_index()
st.bar_chart(calls_per_weekday)

st.subheader("Risposte vs Non risposte per giorno")
status_per_day = df.groupby(['weekday', 'status']).size().unstack(fill_value=0).loc[ordered_days]
st.bar_chart(status_per_day)

st.subheader("Chiamate per ora del giorno")
calls_by_hour = df.groupby('hour').size()
st.bar_chart(calls_by_hour)

st.subheader("Risposte vs Non risposte per ora")
status_by_hour = df.groupby(['hour', 'status']).size().unstack(fill_value=0).sort_index()
st.bar_chart(status_by_hour)

# ------------------------ ANALISI AVANZATE ------------------------
st.header("📊 Analisi avanzate")

st.subheader("Distribuzione NON risposte per ora")
missed_by_hour = df[df['status'] == 'NOTSERVED'].groupby('hour').size()
st.bar_chart(missed_by_hour)

st.subheader("⏱️ Attesa media per ora")
wait_by_hour = df.groupby('hour')['waitingTime'].mean() / 60
st.line_chart(wait_by_hour)

st.subheader("⏳ Attesa media delle NON risposte")
wait_nots = df[df['status'] == 'NOTSERVED']['waitingTime'] / 60
if not wait_nots.empty:
    st.metric("Attesa media (non risposte)", f"{round(wait_nots.mean(), 1)} min")

# ------------------------ CHIAMANTI RICORRENTI ------------------------
st.header("👥 Analisi chiamanti")

st.subheader("Top 10 chiamanti ricorrenti")
top_callers = df['callerId'].value_counts().head(10)
st.bar_chart(top_callers)

st.subheader("Ripetizione chiamate (fino a 5)")
repeat_calls = df.groupby('callerId').size().reset_index(name='num_calls')
repeat_stats = repeat_calls[repeat_calls['num_calls'] <= 5]['num_calls'].value_counts().sort_index()
st.bar_chart(repeat_stats)

# 🔄 Analisi richiami
st.subheader("🔄 Analisi richiami")

# Tempo medio tra tentativi (in ore)
answered_df = df[df['status'] == 'SERVED'].sort_values(by='startTime')
answered_df['prev_call_time'] = answered_df.groupby('callerId')['startTime'].shift(1)
answered_df['delta_to_answer'] = (answered_df['answerTime'] - answered_df['prev_call_time']).dt.total_seconds()

avg_delta_hr = round(answered_df['delta_to_answer'].mean(skipna=True) / 3600, 2)
st.metric("⏱️ Tempo medio tra tentativi fino a risposta", f"{avg_delta_hr} h")

# Distribuzione tempi richiamo in blocchi di 6h
delta_hours = answered_df['delta_to_answer'].dropna() / 3600
bins = [0, 6, 12, 18, 24, 30, 36, 42, 48, 72, np.inf]
labels = ['0–6h', '6–12h', '12–18h', '18–24h', '24–30h', '30–36h', '36–42h', '42–48h', '48–72h', '72h+']
binned = pd.cut(delta_hours, bins=bins, labels=labels, right=False)
bin_counts = binned.value_counts().sort_index()

st.bar_chart(bin_counts)

# Percentuale utenti che ottengono risposta alla seconda chiamata
calls_sorted = df[df['direction'] == 'IN'].sort_values(['callerId', 'startTime'])
calls_sorted['call_rank'] = calls_sorted.groupby('callerId').cumcount() + 1

# Seleziona utenti con almeno 2 chiamate
second_calls = calls_sorted[calls_sorted['call_rank'] == 2]
first_calls = calls_sorted[calls_sorted['call_rank'] == 1]

# Unisci prima e seconda per ogni utente
merged = pd.merge(
    first_calls[['callerId', 'status']],
    second_calls[['callerId', 'status']],
    on='callerId',
    suffixes=('_first', '_second')
)

# Condizione: prima NOTSERVED e seconda SERVED
got_answer_on_second = merged[
    (merged['status_first'] == 'NOTSERVED') &
    (merged['status_second'] == 'SERVED')
]

total_two_calls = len(merged)
percent_second_try_success = 100 * len(got_answer_on_second) / total_two_calls if total_two_calls else 0

st.metric("✅ Risposta alla 2ª chiamata", f"{percent_second_try_success:.1f}%")



# ------------------------ HEATMAP E DESTINAZIONI ------------------------
st.header("🧭 Distribuzione avanzata")

st.subheader("Heatmap chiamate giorno × ora")
pivot_heatmap = df.pivot_table(index='weekday', columns='hour', values='callerId', aggfunc='count', fill_value=0)
st.dataframe(pivot_heatmap)

st.subheader("Durata media per destinazione")
conversation_by_dest = df[df['status'] == 'SERVED'].groupby('detailDestinationName')['conversationTime'].mean() / 60
conversation_by_dest = conversation_by_dest.sort_values(ascending=False)
st.bar_chart(conversation_by_dest)
