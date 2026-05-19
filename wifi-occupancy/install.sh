#!/bin/bash
# WiFi Occupancy - Script de Instalacao
# Correr no Raspberry Pi como islab (com sudo)

set -e

echo "============================================"
echo "  WiFi Occupancy - Instalacao"
echo "============================================"

# 1. Diretorios
echo "[1/6] Criando diretorios..."
mkdir -p /home/islab/wifi-occupancy/{data/{raw,db,model},logs,services}
cd /home/islab/wifi-occupancy

# 2. Dependencias Python
echo "[2/6] Instalando dependencias Python..."
pip3 install --user streamlit plotly pandas scikit-learn numpy 2>/dev/null || pip3 install streamlit plotly pandas scikit-learn numpy

# 3. Permissoes
echo "[3/6] Configurando permissoes..."
chmod +x /home/islab/wifi-occupancy/*.sh
chmod +x /home/islab/wifi-occupancy/*.py

# 4. Systemd
echo "[4/6] Instalando servicos systemd..."
sudo cp /home/islab/wifi-occupancy/services/*.service /home/islab/wifi-occupancy/services/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# 5. Ativar servicos
echo "[5/6] Ativando servicos..."
sudo systemctl enable wifi-channel-hop.service
sudo systemctl enable wifi-capture.service
sudo systemctl enable wifi-process.timer
sudo systemctl enable wifi-dashboard.service

echo ""
echo "============================================"
echo "  Instalacao completa!"
echo "============================================"
echo ""
echo "Para iniciar tudo:"
echo "  sudo systemctl start wifi-channel-hop"
echo "  sudo systemctl start wifi-capture"
echo "  sudo systemctl start wifi-process.timer"
echo "  sudo systemctl start wifi-dashboard"
echo ""
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "Ver logs:"
echo "  tail -f /home/islab/wifi-occupancy/logs/*.log"
echo ""
echo "IMPORTANTE:"
echo "  1. O adaptador wlan1 deve estar em modo monitor antes de iniciar"
echo "  2. Para colocar em modo monitor:"
echo "     sudo ip link set wlan1 down"
echo "     sudo iw dev wlan1 set type monitor"
echo "     sudo ip link set wlan1 up"
echo ""
