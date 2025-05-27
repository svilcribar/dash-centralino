import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

st.set_page_config(page_title="Dashboard Centralino", layout="wide")

# URL al foglio Google Sheets esportato come CSV
sheet_url = "https://docs.google.com/spreadsheets/d/1QbYg-2NgpzfoGB-jI0Rm8CJvS6dvK2nVLst52Z3P7os/export?format=csv"

@st.cache_data
def load_data():
    df = pd.read_csv(sheet_url, parse_dates=["start_datetime", "answer_datetime", "end_datetime"])
    return df

df = load_data()

st.title("📞 Dashboard Centralino")
st.markdown("Analisi delle chiamate ricevute dal centralino")

# Preprocessing
col1, col2 = st.columns(2)
with col1:
    st.metric("Totale chiamate", len(df))
    st.metric("Chiamate risposte", df['answer_datetime'].notna().sum())
    st.metric("Chiamate non risposte", df['answer_datetime'].isna().sum())

with col2:
    chiamanti_unici = df['caller'].nunique()
    st.metric("Numeri unici chiamanti", chiamanti_unici)
    media_attesa = (df['answer_datetime'] - df['start_datetime']).dropna().mean()
    st.metric("Tempo medio di attesa", f"{media_attesa.seconds//60} min {media_attesa.seconds%60} sec")

# Chiamate per giorno
df['giorno'] = df['start_datetime'].dt.date
chiamate_giornaliere = df.groupby('giorno').size()
st.line_chart(chiamate_giornaliere, use_container_width=True)

# Analisi per operatore
st.subheader("📊 Analisi per operatore")
risposte = df[df['answer_datetime'].notna()]
operatore_stats = risposte.groupby('answered_by').agg(
    chiamate=('caller', 'count'),
    durata_media=('conversationTime', 'mean')
)
st.dataframe(operatore_stats)

fig1, ax1 = plt.subplots()
operatore_stats['chiamate'].plot(kind='bar', ax=ax1, color='lightgreen')
ax1.set_ylabel("N. chiamate")
ax1.set_title("Numero di chiamate per operatore")
st.pyplot(fig1)

# Analisi richiamanti
st.subheader("🔁 Analisi dei richiamanti")
ripetizioni = df.groupby('caller').size().value_counts().sort_index()
fig2, ax2 = plt.subplots()
ripetizioni.plot(kind='bar', ax=ax2, color='lightcoral')
ax2.set_xlabel("Numero di chiamate effettuate")
ax2.set_ylabel("Numero di chiamanti")
ax2.set_title("Distribuzione dei richiamanti")
st.pyplot(fig2)

# Analisi tempo prima della risposta dopo una chiamata non risolta
st.subheader("⏱️ Tempo medio prima che una chiamata persa venga richiamata")
df_sorted = df.sort_values(by=['caller', 'start_datetime'])
df_sorted['answered'] = df_sorted['answer_datetime'].notna()

rows = []
for caller, group in df_sorted.groupby('caller'):
    last_missed = None
    for _, row in group.iterrows():
        if not row['answered']:
            last_missed = row['start_datetime']
        elif last_missed:
            delta = (row['start_datetime'] - last_missed).total_seconds()
            rows.append(delta)
            last_missed = None

if rows:
    time_to_answer_after_missed = pd.Series(rows)
    fig3, ax3 = plt.subplots()
    ax3.hist(time_to_answer_after_missed / 60, bins=30, color='skyblue', edgecolor='black')
    ax3.set_title("Tempo prima di risposta dopo una chiamata persa (minuti)")
    ax3.set_xlabel("Minuti")
    ax3.set_ylabel("Numero di chiamate")
    st.pyplot(fig3)
else:
    st.info("Non ci sono dati sufficienti per questa analisi.")
