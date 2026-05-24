import sqlite3
import os
import time
from datetime import datetime, timedelta
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import OPTICS

# ==========================================
# MANUAL CONFIGURATION REQUIRED
# ==========================================
DATA_DIR = "data"
RAW_DB_PATH = os.path.join(DATA_DIR, "raw_packets.db")
DASHBOARD_DB_PATH = os.path.join(DATA_DIR, "device_counts.db")
WINDOW_MINUTES = 5
UPDATE_INTERVAL_SECONDS = 60
# ==========================================

def init_dashboard_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DASHBOARD_DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS device_counts (
            window TEXT PRIMARY KEY,
            probe_count INTEGER,
            estimated_devices INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def fetch_recent_packets() -> pd.DataFrame:
    if not os.path.exists(RAW_DB_PATH):
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(RAW_DB_PATH)
        cutoff_time = (datetime.now() - timedelta(minutes=WINDOW_MINUTES)).timestamp()
        
        df = pd.read_sql_query(
            f"SELECT timestamp, mac, rssi FROM raw_probes WHERE timestamp >= {cutoff_time}",
            conn
        )
        conn.close()
        return df
    except sqlite3.Error:
        return pd.DataFrame()

def process_and_cluster(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    df_clean = df.dropna(subset=['rssi']).copy()
    
    if len(df_clean) < 3:
        return len(df_clean['mac'].unique())

    X = df_clean[['timestamp', 'rssi']].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    optics = OPTICS(min_samples=3, xi=0.05, metric='euclidean')
    labels = optics.fit_predict(X_scaled)

    unique_clusters = set(labels)
    if -1 in unique_clusters:
        unique_clusters.remove(-1)

    return len(unique_clusters)

def save_to_dashboard(probe_count: int, estimated_devices: int):
    conn = sqlite3.connect(DASHBOARD_DB_PATH)
    current_window = datetime.now().replace(second=0, microsecond=0).isoformat()
    
    conn.execute('''
        INSERT OR REPLACE INTO device_counts 
        (window, probe_count, estimated_devices)
        VALUES (?, ?, ?)
    ''', (current_window, probe_count, estimated_devices))
    
    conn.commit()
    conn.close()
    print(f"[{current_window}] Processed {probe_count} probes -> Counted {estimated_devices} devices.")

def main():
    print("Starting OPTICS Engine...")
    init_dashboard_db()
    
    while True:
        start_time = time.time()
        
        df_raw = fetch_recent_packets()
        devices = process_and_cluster(df_raw)
        save_to_dashboard(len(df_raw), devices)
        
        elapsed = time.time() - start_time
        sleep_time = max(0, UPDATE_INTERVAL_SECONDS - elapsed)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()