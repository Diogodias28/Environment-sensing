import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import time

# ==========================================
# MANUAL CONFIGURATION REQUIRED
# ==========================================
DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "device_counts.db")
# ==========================================

st.set_page_config(page_title="WiFi Device Counter", layout="wide")

@st.cache_data(ttl=30)
def fetch_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT window, probe_count, estimated_devices FROM device_counts ORDER BY window DESC LIMIT 1000",
        conn,
        parse_dates=['window']
    )
    conn.close()
    
    if not df.empty:
        df = df.sort_values(by="window")
    
    return df

def main():
    st.title("📡 Live WiFi Device Counter (OPTICS Physics Engine)")

    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}")
        st.info("Ensure server_api.py and heavy_lifter.py are running.")
        st.stop()

    df = fetch_data()

    if df.empty:
        st.warning("No data available yet. Waiting for heavy_lifter.py to process the first batch...")
        st.stop()

    # Get the latest rolling window data
    latest = df.iloc[-1]
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Physical Devices", int(latest['estimated_devices']))
    with col2:
        st.metric("Raw Probes Processed", int(latest['probe_count']))
    with col3:
        st.metric("Last Updated", latest['window'].strftime('%H:%M:%S'))

    st.divider()

    st.subheader("Device Count Trend (Rolling Windows)")
    fig = px.line(
        df, 
        x='window', 
        y='estimated_devices',
        labels={'window': 'Time', 'estimated_devices': 'Counted Devices'},
        title="Physical Devices Detected Over Time"
    )
    fig.update_traces(line_color='#2ecc71', line_width=3)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Raw Probe Volume vs Processed Devices")
    fig2 = px.bar(
        df,
        x='window',
        y=['probe_count', 'estimated_devices'],
        barmode='overlay',
        labels={'value': 'Count', 'variable': 'Metric', 'window': 'Time'},
        title="Impact of MAC Randomization Filter (Raw Probes vs Actual Devices)"
    )
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("View Raw Database Output"):
        st.dataframe(df.tail(20).sort_values(by="window", ascending=False), use_container_width=True)

    st.caption("Data updates every 30 seconds. Reload the page or click below to force refresh.")
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()