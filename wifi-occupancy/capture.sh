#!/bin/bash
# WiFi Probe Request Capture Service v2
# Garante que o diretório existe antes de capturar

INTERFACE="wlan1"
CAPTURE_DIR="/home/islab/wifi-occupancy/data/raw"

# Criar diretório se não existir (com permissões explícitas)
mkdir -p "$CAPTURE_DIR"
chmod 777 "$CAPTURE_DIR"

# Verificar se conseguimos escrever
touch "$CAPTURE_DIR/.write_test" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERRO: Não consigo escrever em $CAPTURE_DIR"
    echo "A usar /tmp como fallback..."
    CAPTURE_DIR="/tmp"
fi
rm -f "$CAPTURE_DIR/.write_test"

echo "Capturando em: $CAPTURE_DIR"

sudo tshark -i "$INTERFACE"   -f "type mgt subtype probe-req"   -w "$CAPTURE_DIR/bib.pcap"   -b filesize:25000   -b files:40   -b duration:900
