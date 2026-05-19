#!/usr/bin/env python3
"""
WiFi Occupancy Dashboard
Streamlit app que le do SQLite local
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

DB_PATH = "/home/islab/wifi-occupancy/data/db/occupancy.db"

st.set_page_config(page_title="Biblioteca - Ocupacao WiFi", layout="wide")

# ============================================================
# CACHE DE DADOS
# ============================================================

@st.cache_data(ttl=60)
def get_recent_occupancy(hours=24):
    conn = sqlite3.connect(DB_PATH)
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    df = pd.read_sql_query(
        f"SELECT * FROM occupancy WHERE window > '{since}' ORDER BY window",
        conn, parse_dates=['window']
    )
    conn.close()
    return df

@st.cache_data(ttl=300)
def get_daily_stats(days=7):
    conn = sqlite3.connect(DB_PATH)
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    df = pd.read_sql_query(
        f"SELECT * FROM daily_stats WHERE date > '{since}' ORDER BY date",
        conn
    )
    conn.close()
    return df

@st.cache_data(ttl=60)
def get_all_occupancy():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM occupancy ORDER BY window DESC LIMIT 1000",
        conn, parse_dates=['window']
    )
    conn.close()
    return df

# ============================================================
# UI
# ============================================================

st.title("📚 Ocupacao da Biblioteca (WiFi Probe Requests)")

# Verificar se DB existe
if not os.path.exists(DB_PATH):
    st.error(f"Base de dados nao encontrada: {DB_PATH}")
    st.info("Corre o pipeline primeiro: python3 process.py")
    st.stop()

# KPIs
df_recent = get_recent_occupancy(24)

if df_recent.empty:
    st.warning("Nenhum dado nas ultimas 24h. O pipeline esta a correr?")
    st.stop()

# Ocupacao atual
latest = df_recent.iloc[-1]
occ_colors = {
    'Vazia': '#2ecc71', 'Pouca Gente': '#f1c40f',
    'Media': '#e67e22', 'Cheia': '#e74c3c', 'Muito Cheia': '#c0392b'
}
color = occ_colors.get(latest['occupancy_label'], '#95a5a6')

# Layout em colunas
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f""""
    <div style='background-color:{color}; padding:20px; border-radius:10px; text-align:center;'>
        <h2 style='color:white; margin:0;'>{latest['occupancy_label']}</h2>
        <p style='color:white; margin:0;'>Ocupacao Atual</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.metric("Probes / 15min", int(latest['probe_count']))

with col3:
    st.metric("MACs Unicos", int(latest['unique_macs']))

with col4:
    st.metric("RSSI Medio", f"{latest['rssi_mean']:.1f} dBm")

st.caption(f"Ultima atualizacao: {latest['window'].strftime('%H:%M')}")

# Tabs
tab1, tab2, tab3 = st.tabs(["Tempo Real", "Historico", "Heatmap"])

with tab1:
    st.subheader("Ultimas 24 Horas")

    fig = px.line(df_recent, x='window', y='probe_count',
                  color='occupancy_label',
                  color_discrete_map=occ_colors,
                  labels={'window': 'Hora', 'probe_count': 'Probe Requests'},
                  title="Ocupacao ao longo do tempo")
    st.plotly_chart(fig, use_container_width=True)

    # Tabela
    st.dataframe(df_recent[['window', 'occupancy_label', 'probe_count', 
                            'unique_macs', 'rssi_mean']].tail(10),
                 use_container_width=True)

with tab2:
    st.subheader("Estatisticas Diarias")
    df_daily = get_daily_stats(7)

    if not df_daily.empty:
        fig2 = px.bar(df_daily, x='date', y='avg_occupancy',
                      labels={'date': 'Data', 'avg_occupancy': 'Ocupacao Media'},
                      title="Media de Ocupacao por Dia")
        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(df_daily, use_container_width=True)
    else:
        st.info("Ainda nao ha dados diarios suficientes.")

with tab3:
    st.subheader("Heatmap (Hora vs Dia)")
    df_all = get_all_occupancy()

    if not df_all.empty:
        df_all['hour'] = df_all['window'].dt.hour
        df_all['day_name'] = df_all['window'].dt.day_name()

        occ_map = {'Vazia': 0, 'Pouca Gente': 1, 'Media': 2, 'Cheia': 3, 'Muito Cheia': 4}
        df_all['occ_val'] = df_all['occupancy_label'].map(occ_map).fillna(0)

        pivot = df_all.pivot_table(values='occ_val', index='hour', 
                                   columns='day_name', aggfunc='mean')
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                     'Friday', 'Saturday', 'Sunday']
        pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])

        fig3 = px.imshow(pivot, aspect='auto', color_continuous_scale='RdYlGn_r',
                         labels=dict(color="Ocupacao"),
                         title="Padrao de Ocupacao")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Dados insuficientes para heatmap.")

# Footer
st.divider()
st.caption("Dados anonimizados. Atualiza a cada 60 segundos. Recarrega a pagina para ver novos dados.")
