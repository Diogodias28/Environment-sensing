#!/bin/bash
# WiFi Probe Request Capture Service
# Corre continuamente, roda ficheiros a cada ~15 min

INTERFACE="wlan1"
CAPTURE_DIR="/home/islab/wifi-occupancy/data/raw"
sudo mkdir -p "$CAPTURE_DIR"

# Tshark contínuo com rotação
# -b filesize:25000 ≈ 15 min de probes
# -b files:40 = últimas 10h de dados
sudo tshark -i "$INTERFACE"   -f "type mgt subtype probe-req"   -w "$CAPTURE_DIR/bib.pcap"
