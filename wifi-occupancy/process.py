#!/usr/bin/env python3
"""
WiFi Occupancy Pipeline
Processa pcap mais recente -> extrai features -> classifica -> SQLite
"""

import os
import glob
import hashlib
import sqlite3
import json
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, OPTICS
from sklearn.metrics import silhouette_score

# ============================================================
# CONFIG
# ============================================================
DATA_DIR = "/var/wifi-occupancy/data"
RAW_DIR = os.path.join(DATA_DIR, "raw")
DB_PATH = os.path.join(DATA_DIR, "db", "occupancy.db")
MODEL_PATH = os.path.join(DATA_DIR, "model", "model_config.json")
WINDOW_MINUTES = 15
FEATURE_COLS = ['probe_count', 'unique_macs', 'rssi_mean',
                'rssi_std', 'ssid_diversity', 'mac_randomization_ratio']
# Filtros de proximidade
RSSI_MIN_DBM     = -65      # descarta dispositivos fora da sala
SSID_KNOWN       = {        # mantém probes destes SSIDs (adapta ao teu campus)
    "eduroam"
}
SSID_KEEP_WILDCARD = True   # mantém sempre probes sem SSID (wildcard)
os.makedirs(os.path.join(DATA_DIR, "db"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "model"), exist_ok=True)

# ============================================================
# 1. EXTRACT FROM PCAP
# ============================================================

def extract_from_pcap(pcap_file):
    """Extrai probe requests usando tshark."""
    cmd = [
        "tshark", "-r", pcap_file,
        "-T", "fields",
        "-e", "frame.time_epoch",
        "-e", "wlan.sa",
        "-e", "radiotap.dbm_antsignal",
        "-e", "wlan.ssid",
        "-E", "header=n", "-E", "separator=\t", "-E", "quote=d",
        "-Y", "wlan.fc.type_subtype == 0x04"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print("tshark erro:", result.stderr)
            return pd.DataFrame()
    except Exception as e:
        print("Erro a correr tshark:", e)
        return pd.DataFrame()

    lines = result.stdout.strip().split("\n")
    data = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 4:
            try:
                ts = float(parts[0].strip('"'))
                mac = parts[1].strip('"')
                rssi_raw = parts[2].strip('"')
                rssi = float(rssi_raw.split(',')[0]) if rssi_raw else None
                ssid = parts[3].strip('"') if len(parts) > 3 else ""
                data.append({
                    'timestamp': datetime.fromtimestamp(ts),
                    'mac': mac,
                    'rssi': rssi,
                    'ssid': "Wildcard" if (not ssid or ssid == "<MISSING>") else ssid
                })
            except:
                continue

    return pd.DataFrame(data)


# ============================================================
# 2. ANONYMIZE
# ============================================================

def anonymize_mac(mac):
    if not mac or len(mac) < 9:
        return "unknown"
    oui = mac[:9]
    last3 = mac[9:]
    hashed = hashlib.sha512(last3.encode()).hexdigest()[:6]
    return f"{oui}{hashed}"

def filter_probes(df):
    """Remove probes de fora da sala por RSSI e SSID irrelevante."""
    if df.empty:
        return df

    before = len(df)
    print(f"  RSSI sample: {df['rssi'].head(5).tolist()}")
    print(f"  RSSI not null: {df['rssi'].notna().sum()}")
    print(f"  SSID sample: {df['ssid'].head(5).tolist()}")
    after_rssi = df[df['rssi'].notna() & (df['rssi'] >= RSSI_MIN_DBM)]
    print(f"  Após RSSI (-65): {len(after_rssi)}")
    # 1. Filtro RSSI — descarta sinais fracos (dispositivos longe)
    df = df[df['rssi'].notna() & (df['rssi'] >= RSSI_MIN_DBM)]

    # 2. Filtro SSID — mantém wildcards + SSIDs institucionais conhecidos
    if SSID_KNOWN:
        ssid_lower = df['ssid'].str.lower()
        known_lower = {s.lower() for s in SSID_KNOWN}
        mask_wildcard = (df['ssid'] == 'Wildcard') if SSID_KEEP_WILDCARD else False
        mask_known    = ssid_lower.isin(known_lower)
        df = df[mask_wildcard | mask_known]

    after = len(df)
    pct = (1 - after / before) * 100 if before > 0 else 0
    print(f"  Filtro: {before:,} → {after:,} probes ({pct:.0f}% descartados)")
    return df


def estimate_optics_devices(group_df):
    """Estima número de dispositivos físicos numa janela usando OPTICS clustering."""
    if group_df.empty:
        return 0

    df_clean = group_df.dropna(subset=['rssi']).copy()
    if len(df_clean) < 3:
        return int(df_clean['mac'].nunique())

    X = df_clean[['timestamp', 'rssi']].values
    X[:, 0] = pd.to_datetime(X[:, 0]).view('int64') / 10**9

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    optics = OPTICS(min_samples=3, xi=0.05, metric='euclidean')
    labels = optics.fit_predict(X_scaled)

    unique_clusters = set(labels)
    if -1 in unique_clusters:
        unique_clusters.remove(-1)

    return len(unique_clusters)


# ============================================================
# 3. FEATURE ENGINEERING
# ============================================================

def extract_features(df, window_minutes=15):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df['window'] = df['timestamp'].dt.floor(f'{window_minutes}min')

    features = []
    for window, group in df.groupby('window'):
        probe_count = len(group)
        unique_macs = group['mac'].nunique()
        rssi_mean = group['rssi'].mean() if group['rssi'].notna().any() else -80
        rssi_std = group['rssi'].std() if group['rssi'].notna().sum() > 1 else 0
        ssid_diversity = group['ssid'].nunique()

        macs = group['mac'].unique()
        randomized = sum(1 for m in macs if len(m) > 1 and m[1] in '26aAeE')
        mac_rand_ratio = randomized / len(macs) if len(macs) > 0 else 0

        optics_estimated_devices = estimate_optics_devices(group)

        hour = window.hour
        day_of_week = window.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0

        features.append({
            'window': window,
            'probe_count': probe_count,
            'unique_macs': unique_macs,
            'rssi_mean': rssi_mean,
            'rssi_std': rssi_std,
            'ssid_diversity': ssid_diversity,
            'mac_randomization_ratio': mac_rand_ratio,
            'optics_estimated_devices': optics_estimated_devices,
            'hour': hour,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend
        })

    return pd.DataFrame(features)


# ============================================================
# 4. MODEL
# ============================================================

def train_or_load_model(df_features):
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'r') as f:
            config = json.load(f)
        print("Modelo carregado de", MODEL_PATH)
        return config

    print("Treinando novo modelo...")
    X = df_features[FEATURE_COLS].fillna(0)

    if len(X) < 10:
        print("Dados insuficientes para treinar")
        return None

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    best_k, best_score = 3, -1
    for k in range(2, min(6, len(X))):
        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X_scaled)
            score = silhouette_score(X_scaled, labels)
            if score > best_score:
                best_score = score
                best_k = k
        except:
            continue
    # replace nisto
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    df_temp = df_features.copy()
    df_temp['cluster'] = labels
    cluster_means = df_temp.groupby('cluster')['probe_count'].mean().sort_values()

    labels_text = ['Vazia', 'Pouca Gente', 'Média', 'Cheia', 'Muito Cheia']
    mapping = {}
    for i, (cluster_id, _) in enumerate(cluster_means.items()):
        mapping[str(cluster_id)] = labels_text[i] if i < len(labels_text) else f'Cluster_{cluster_id}'

    config = {
        'scaler_mean': scaler.mean_.tolist(),
        'scaler_scale': scaler.scale_.tolist(),
        'kmeans_centers': kmeans.cluster_centers_.tolist(),
        'kmeans_labels_map': mapping,
        'n_clusters': best_k,
        'trained_at': datetime.now().isoformat(),
        'window_minutes': WINDOW_MINUTES
    }

    with open(MODEL_PATH, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Modelo treinado: K={best_k}")
    print(f"Mapeamento: {mapping}")
    return config


def classify_window(features, config):
    if config is None:
        return None, "Desconhecido"

    x = np.array([features[col] for col in FEATURE_COLS])
    mean = np.array(config['scaler_mean'])
    scale = np.array(config['scaler_scale'])
    x_scaled = (x - mean) / scale

    centers = np.array(config['kmeans_centers'])
    distances = np.linalg.norm(centers - x_scaled, axis=1)
    cluster_id = int(np.argmin(distances))

    label = config['kmeans_labels_map'].get(str(cluster_id), f'Cluster_{cluster_id}')
    return cluster_id, label


# ============================================================
# 5. SQLITE
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS occupancy (
            window TEXT PRIMARY KEY,
            probe_count INTEGER,
            unique_macs INTEGER,
            rssi_mean REAL,
            rssi_std REAL,
            ssid_diversity INTEGER,
            mac_randomization_ratio REAL,
            optics_estimated_devices INTEGER,
            hour INTEGER,
            day_of_week INTEGER,
            is_weekend INTEGER,
            cluster INTEGER,
            occupancy_label TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            avg_occupancy REAL,
            peak_hour INTEGER,
            peak_probe_count INTEGER,
            total_windows INTEGER,
            weekend INTEGER
        )
    ''')

    # Migração: adicionar optics_estimated_devices se não existir
    try:
        c.execute("ALTER TABLE occupancy ADD COLUMN optics_estimated_devices INTEGER")
        conn.commit()
        print("Coluna optics_estimated_devices adicionada (migração)")
    except sqlite3.OperationalError:
        pass  # coluna já existe

    conn.close()
    print("Base de dados inicializada")


def save_to_db(df_results):
    if df_results.empty:
        return

    conn = sqlite3.connect(DB_PATH)

    for _, row in df_results.iterrows():
        conn.execute('''
            INSERT OR REPLACE INTO occupancy
            (window, probe_count, unique_macs, rssi_mean, rssi_std, ssid_diversity,
             mac_randomization_ratio, optics_estimated_devices, hour, day_of_week, is_weekend, cluster, occupancy_label)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['window'].isoformat(), row['probe_count'], row['unique_macs'],
            row['rssi_mean'], row['rssi_std'], row['ssid_diversity'],
            row['mac_randomization_ratio'], int(row['optics_estimated_devices']),
            row['hour'], row['day_of_week'],
            row['is_weekend'], row['cluster'], row['occupancy_label']
        ))

    df_results['date'] = df_results['window'].dt.date.astype(str)
    for date, group in df_results.groupby('date'):
        occupancy_map = {'Vazia': 0, 'Pouca Gente': 1, 'Média': 2, 'Cheia': 3, 'Muito Cheia': 4}
        group['occ_val'] = group['occupancy_label'].map(occupancy_map).fillna(0)

        avg_occ = group['occ_val'].mean()
        peak_row = group.loc[group['probe_count'].idxmax()]

        conn.execute('''
            INSERT OR REPLACE INTO daily_stats
            (date, avg_occupancy, peak_hour, peak_probe_count, total_windows, weekend)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            date, avg_occ, int(peak_row['hour']), int(peak_row['probe_count']),
            len(group), int(peak_row['is_weekend'])
        ))

    conn.commit()
    conn.close()
    print(f"{len(df_results)} janelas guardadas no SQLite")


# ============================================================
# 6. MAIN
# ============================================================

def main():
    print("=" * 60)
    print("WiFi Occupancy Pipeline")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    init_db()

    pcap_files = sorted(glob.glob(os.path.join(RAW_DIR, "bib*.pcap")), key=os.path.getmtime)
    if not pcap_files:
        print("Nenhum pcap encontrado em", RAW_DIR)
        return

    pcap_file = pcap_files[-1]
    print(f"A processar: {os.path.basename(pcap_file)}")

    df_raw = extract_from_pcap(pcap_file)
    if df_raw.empty:
        print("Nenhum probe request encontrado")
        return

    print(f"  {len(df_raw):,} probes extraidos")

    df_raw['mac'] = df_raw['mac'].apply(anonymize_mac)
    
    df_raw = filter_probes(df_raw)
    if df_raw.empty:
        print("Nenhum probe sobrou após filtragem — ajusta os limiares")
        return

    df_features = extract_features(df_raw, WINDOW_MINUTES)
    if df_features.empty:
        print("Nenhuma janela criada")
        return

    print(f"  {len(df_features)} janelas de {WINDOW_MINUTES}min")

    config = train_or_load_model(df_features)

    if config:
        df_features['cluster'] = -1
        df_features['occupancy_label'] = "Desconhecido"
        for idx, row in df_features.iterrows():
            cid, label = classify_window(row, config)
            df_features.at[idx, 'cluster'] = cid
            df_features.at[idx, 'occupancy_label'] = label
    else:
        q33 = df_features['probe_count'].quantile(0.33)
        q66 = df_features['probe_count'].quantile(0.66)
        def fallback_label(x):
            if x <= q33: return 'Vazia'
            elif x <= q66: return 'Pouca Gente'
            else: return 'Média'
        df_features['occupancy_label'] = df_features['probe_count'].apply(fallback_label)
        df_features['cluster'] = df_features['occupancy_label'].astype('category').cat.codes

    save_to_db(df_features)

    print("\nResumo da ultima janela:")
    last = df_features.iloc[-1]
    print(f"  {last['window']} -> {last['occupancy_label']} ({last['probe_count']} probes, {last['unique_macs']} MACs, OPTICS={last['optics_estimated_devices']} devices)")

    print("\nPipeline concluido!")


if __name__ == "__main__":
    main()
