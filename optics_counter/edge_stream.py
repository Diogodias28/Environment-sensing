import subprocess
import requests
import sys
import hashlib

# ==========================================
# MANUAL CONFIGURATION REQUIRED
# ==========================================
BACKEND_URL = "http://192.168.137.X:5000/ingest"
INTERFACE = "wlan1"
BATCH_SIZE = 50
# ==========================================

def anonymize_mac(mac_string: str) -> str:
    return hashlib.sha256(mac_string.encode('utf-8')).hexdigest()

def stream_packets():
    cmd = [
        "tshark", "-i", INTERFACE,
        "-l",
        "-T", "fields",
        "-e", "frame.time_epoch",
        "-e", "wlan.sa",
        "-e", "radiotap.dbm_antsignal",
        "-E", "header=n", "-E", "separator=,", "-E", "quote=d",
        "-Y", "wlan.fc.type_subtype == 0x04"
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    except FileNotFoundError:
        print("Error: tshark is not installed. Run 'sudo apt install tshark'.")
        sys.exit(1)

    session = requests.Session()
    batch = []

    for line in iter(process.stdout.readline, ""):
        parts = line.strip().split(",")
        if len(parts) < 3:
            continue
        
        try:
            rssi_str = parts[2].strip('"')
            if not rssi_str:
                continue
            
            raw_mac = parts[1].strip('"')
            
            packet = {
                'timestamp': float(parts[0].strip('"')),
                'mac': anonymize_mac(raw_mac),
                'rssi': float(rssi_str)
            }
            batch.append(packet)

            if len(batch) >= BATCH_SIZE:
                try:
                    session.post(BACKEND_URL, json=batch, timeout=3)
                except requests.RequestException:
                    pass
                finally:
                    batch.clear()
                    
        except ValueError:
            continue

if __name__ == "__main__":
    stream_packets()
