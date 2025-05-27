import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Configurazione pagina
st.set_page_config(page_title="Dashboard Centralino", layout="wide")
st.title("📱 Dashboard Chiamate Centralino")

# URL pubblico Google Sheets CSV export (modifica il link con il tuo ID foglio)
sheet_url = "https://docs.google.com/spreadsheets/d/1QbYg-2NgpzfoGB-jI0Rm8CJvS6dvK2nVLst52Z3P7os/export?format=csv"

@st.cache_data
def load_data(url):
    df = pd.read_csv(url, parse_dates=['start_datetime', 'answer_datetime', 'end_datetime'])
    df['answered'] = df['answer_datetime'].notna()
    df['wait_time'] = (df['answer_datetime'] - df['start_datetime']).dt.total_seconds()
    df['date'] = df['start_datetime'].dt.date
    df['hour'] = df['start_datetime'].dt.hour
    df['weekday'] = df['start_datetime'].dt.day_name()
    return df

df = load_data(sheet_url)

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Totale chiamate", len(df))
col2.metric("Chiamate risposte", df['answered'].sum())
col3.metric("Non risposte", (~df['answered']).sum())
col4.metric("Chiamanti unici", df['caller'].nunique())

# Grafici principali
st.subheader("🌇 Chiamate per ora del giorno")
calls_per_hour = df.groupby('hour').size()
st.bar_chart(calls_per_hour)

st.subheader("🌌 Chiamate per giorno della settimana")
calls_per_weekday = df['weekday'].value_counts().reindex([
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
])
st.bar_chart(calls_per_weekday)

st.subheader("🕒 Tempo medio di attesa per ora")
wait_by_hour = df.groupby('hour')['wait_time'].mean()
st.line_chart(wait_by_hour)

st.subheader("💼 Analisi per Operatore")
answered_df = df[df['answered'] & df['answered_by'].notna()]
operator_stats = answered_df.groupby('answered_by').agg(
    numero_chiamate=('answered_by', 'count'),
    tempo_totale_conversazione=('conversationTime', 'sum'),
    tempo_medio_conversazione=('conversationTime', 'mean'),
    tempo_medio_attesa=('wait_time', 'mean')
).reset_index()
operator_stats['tempo_totale_conversazione'] /= 60  # minuti
st.dataframe(operator_stats)

# Richiamanti
st.subheader("👥 Analisi dei richiamanti")
df_sorted = df.sort_values(['caller', 'start_datetime'])
df_sorted['next_call_time'] = df_sorted.groupby('caller')['start_datetime'].shift(-1)
df_sorted['time_to_next_call'] = (df_sorted['next_call_time'] - df_sorted['end_datetime']).dt.total_seconds()
df_sorted['got_answer_later'] = df_sorted.groupby('caller')['answered'].transform(lambda x: x.cumsum().shift(-1, fill_value=0))
time_to_answer_after_missed = df_sorted[(~df_sorted['answered']) & (df_sorted['got_answer_later'] > 0)]['time_to_next_call'].dropna()

if not time_to_answer_after_missed.empty:
    st.markdown("**Distribuzione tempo alla richiamata con risposta (in minuti):**")
    st.hist(time_to_answer_after_missed / 60, bins=30)
else:
    st.info("Non ci sono abbastanza dati per questa analisi.")
