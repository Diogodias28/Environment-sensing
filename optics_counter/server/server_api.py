import sqlite3
import os
from flask import Flask, request, jsonify

# ==========================================
# MANUAL CONFIGURATION REQUIRED
# ==========================================
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "raw_packets.db")
PORT = 5000

app = Flask(__name__)

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS raw_probes (
            timestamp REAL,
            mac TEXT,
            rssi REAL
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON raw_probes(timestamp)')
    conn.commit()
    conn.close()

@app.route('/ingest', methods=['POST'])
def ingest():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid or missing JSON payload"}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.executemany('''
            INSERT INTO raw_probes (timestamp, mac, rssi)
            VALUES (:timestamp, :mac, :rssi)
        ''', data)
        conn.commit()
    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()
        
    return jsonify({"status": "success", "inserted": len(data)}), 200

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT)
