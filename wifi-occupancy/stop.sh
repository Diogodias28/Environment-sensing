#!/bin/bash
# WiFi Occupancy - Stop all services

set -e

echo "[1/5] Parando servicos systemd..."
sudo systemctl stop wifi-capture 2>/dev/null || true
sudo systemctl stop wifi-channel-hop 2>/dev/null || true
sudo systemctl stop wifi-process.timer 2>/dev/null || true
sudo systemctl stop wifi-process 2>/dev/null || true
sudo systemctl stop wifi-dashboard 2>/dev/null || true

echo "[2/5] Parando tshark manualmente..."
sudo pkill -f "tshark -i wlan1" 2>/dev/null || true

echo "[3/5] Parando channel hopping..."
sudo pkill -f "iwconfig wlan1 channel" 2>/dev/null || true
sudo pkill -f "iw dev wlan1 set channel" 2>/dev/null || true

echo "[4/5] Parando Streamlit..."
pkill -f "streamlit run" 2>/dev/null || true

echo "[5/5] Restaurando wlan1 para modo managed..."
sudo ip link set wlan1 down 2>/dev/null || true
sudo iw dev wlan1 set type managed 2>/dev/null || true
sudo ip link set wlan1 up 2>/dev/null || true
sudo systemctl start NetworkManager 2>/dev/null || true

echo ""
echo "[OK] Todos os servicos parados."
echo ""
echo "Estado atual:"
sudo systemctl status wifi-capture --no-pager 2>/dev/null || echo "  wifi-capture: parado"
sudo systemctl status wifi-channel-hop --no-pager 2>/dev/null || echo "  wifi-channel-hop: parado"
sudo systemctl status wifi-dashboard --no-pager 2>/dev/null || echo "  wifi-dashboard: parado"
