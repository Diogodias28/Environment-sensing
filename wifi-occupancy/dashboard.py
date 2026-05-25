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

DB_PATH = "/var/wifi-occupancy/data/db/occupancy.db"

st.set_page_config(page_title="Biblioteca - Ocupação WiFi", layout="wide")

OCC_LABELS = ['Vazia', 'Pouca Gente', 'Média', 'Cheia', 'Muito Cheia']
OCC_COLORS = {
    'Vazia': '#2ecc71',
    'Pouca Gente': '#f1c40f',
    'Média': '#e67e22',
    'Cheia': '#e74c3c',
    'Muito Cheia': '#c0392b',
}
OCC_NUMERIC = {'Vazia': 0, 'Pouca Gente': 1, 'Média': 2, 'Cheia': 3, 'Muito Cheia': 4}

TIME_WINDOWS = {
    "Últimas 6 horas": 6,
    "Últimas 12 horas": 12,
    "Últimas 24 horas": 24,
    "Últimos 3 dias": 72,
    "Últimos 7 dias": 168,
}

# ============================================================
# DB HELPER
# ============================================================

def _get_connection():
    return sqlite3.connect(DB_PATH)

# ============================================================
# CACHE DE DADOS
# ============================================================

@st.cache_data(ttl=60)
def get_recent_occupancy(hours=24):
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    conn = _get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM occupancy WHERE window > ? ORDER BY window",
        conn, params=[since], parse_dates=['window']
    )
    conn.close()
    return df


@st.cache_data(ttl=300)
def get_daily_stats(days=7):
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn = _get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM daily_stats WHERE date > ? ORDER BY date",
        conn, params=[since]
    )
    conn.close()
    return df


@st.cache_data(ttl=60)
def get_occupancy_range(hours=168):
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    conn = _get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM occupancy WHERE window > ? ORDER BY window",
        conn, params=[since], parse_dates=['window']
    )
    conn.close()
    return df

# ============================================================
# UI
# ============================================================

st.title("📚 Ocupação da Biblioteca (WiFi Probe Requests)")

if not os.path.exists(DB_PATH):
    st.error(f"Base de dados não encontrada: {DB_PATH}")
    st.info("Corre o pipeline primeiro: python3 process.py")
    st.stop()

# --- Seletor de janela temporal ---
selected_label = st.selectbox(
    "Janela temporal",
    options=list(TIME_WINDOWS.keys()),
    index=2,
    key="time_window",
)
selected_hours = TIME_WINDOWS[selected_label]

# --- Dados ---
df_recent = get_recent_occupancy(selected_hours)

if df_recent.empty:
    st.warning("Nenhum dado no período selecionado. O pipeline está a correr?")
    st.stop()

# --- Ocupação atual ---
latest = df_recent.iloc[-1]
color = OCC_COLORS.get(latest['occupancy_label'], '#95a5a6')

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div style='background-color:{color}; padding:20px; border-radius:10px; text-align:center;'>
        <h2 style='color:white; margin:0;'>{latest['occupancy_label']}</h2>
        <p style='color:white; margin:0;'>Ocupação Atual (KMeans)</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.metric("Probes / 15min", int(latest['probe_count']))

with col3:
    st.metric("MACs Únicos", int(latest['unique_macs']))

with col4:
    optics_val = latest['optics_estimated_devices']
    st.metric("Pessoas (OPTICS)", int(optics_val) if pd.notna(optics_val) else "N/A")

with col5:
    rssi_val = latest['rssi_mean']
    st.metric("RSSI Médio", f"{rssi_val:.1f} dBm" if pd.notna(rssi_val) else "N/A")

st.caption(f"Última atualização: {latest['window'].strftime('%H:%M')} | Período: {selected_label}")

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["Tempo Real", "Histórico", "Heatmap"])

with tab1:
    st.subheader(selected_label)

    fig = go.Figure()
    df_plot = df_recent.sort_values('window').copy()
    df_plot['occ_val'] = df_plot['occupancy_label'].map(OCC_NUMERIC).fillna(0)

    fig.add_trace(go.Scatter(
        x=df_plot['window'], y=df_plot['probe_count'],
        mode='lines+markers',
        line=dict(color='#3498db', width=2),
        marker=dict(
            size=5,
            color=df_plot['occ_val'],
            colorscale=[[0, '#2ecc71'], [0.25, '#f1c40f'],
                        [0.5, '#e67e22'], [0.75, '#e74c3c'], [1, '#c0392b']],
            showscale=False,
        ),
        customdata=df_plot['occupancy_label'],
        hovertemplate='Hora: %{x|%H:%M}<br>Probes: %{y}<br>Estado: %{customdata}<extra></extra>',
        name='Probe Requests',
    ))

    fig.add_trace(go.Scatter(
        x=df_plot['window'], y=df_plot['unique_macs'],
        mode='lines',
        line=dict(color='#e67e22', width=2, dash='dash'),
        name='MACs Únicos',
    ))

    fig.add_trace(go.Scatter(
        x=df_plot['window'], y=df_plot['optics_estimated_devices'],
        mode='lines',
        line=dict(color='#2ecc71', width=3),
        name='OPTICS Estimado',
    ))

    fig.update_layout(
        title="Ocupação ao longo do tempo (KMeans + OPTICS)",
        xaxis_title='Hora', yaxis_title='Contagem',
        hovermode='x unified',
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df_recent[['window', 'occupancy_label', 'probe_count',
                    'unique_macs', 'optics_estimated_devices', 'rssi_mean']].tail(10),
        use_container_width=True,
    )

with tab2:
    days_back = max(1, selected_hours // 24)
    st.subheader(f"Estatísticas Diárias ({days_back} dia{'s' if days_back > 1 else ''})")
    df_daily = get_daily_stats(days_back)

    if not df_daily.empty:
        fig2 = px.bar(
            df_daily, x='date', y='avg_occupancy',
            labels={'date': 'Data', 'avg_occupancy': 'Ocupação Média'},
            title="Média de Ocupação por Dia",
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(df_daily, use_container_width=True)
    else:
        st.info("Ainda não há dados diários suficientes.")

with tab3:
    st.subheader("Heatmap (Hora vs Dia)")
    df_all = get_occupancy_range(selected_hours)

    if not df_all.empty and len(df_all) >= 4:
        df_all['hour'] = df_all['window'].dt.hour
        df_all['day_name'] = df_all['window'].dt.day_name()

        df_all['occ_val'] = df_all['occupancy_label'].map(OCC_NUMERIC).fillna(0)

        pivot = df_all.pivot_table(
            values='occ_val', index='hour',
            columns='day_name', aggfunc='mean',
        )
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                      'Friday', 'Saturday', 'Sunday']
        pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])

        fig3 = px.imshow(
            pivot, aspect='auto', color_continuous_scale='RdYlGn_r',
            labels=dict(color="Ocupação"),
            title=f"Padrão de Ocupação — {selected_label}",
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Dados insuficientes para heatmap.")

# Footer
st.divider()
st.caption("Dados anonimizados. Atualiza a cada 60 segundos. Recarrega a página para ver novos dados.")
