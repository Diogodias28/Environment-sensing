#!/bin/bash
# WiFi Occupancy - Quick Start Manual
# Usar quando nao queres esperar pelo boot

echo "[1/4] Colocando wlan1 em modo monitor..."
sudo ip link set wlan1 down 2>/dev/null
sudo iw dev wlan1 set type monitor 2>/dev/null
sudo ip link set wlan1 up 2>/dev/null
echo "  OK"

echo "[2/4] Criando diretorios..."
mkdir -p /home/islab/wifi-occupancy/{data/{raw,db,model},logs}

echo "[3/4] Iniciando servicos..."
sudo systemctl start wifi-channel-hop
sudo systemctl start wifi-capture
sudo systemctl start wifi-process.timer
sudo systemctl start wifi-dashboard

echo "[4/4] Verificando..."
sleep 2
sudo systemctl status wifi-capture --no-pager
sudo systemctl status wifi-dashboard --no-pager

echo ""
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8501"
echo "Logs: tail -f /home/islab/wifi-occupancy/logs/*.log"
