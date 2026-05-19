#!/bin/bash
# WiFi Occupancy - Quick Start Manual
# Usar quando nao queres esperar pelo boot

echo "[1/4] Colocando wlan1 em modo monitor..."
if ! sudo ip link set wlan1 down; then
    echo "  ERRO: wlan1 nao encontrado - verifica se o adaptador esta ligado!"
    exit 1
fi
sudo iw dev wlan1 set type monitor
sudo ip link set wlan1 up
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
