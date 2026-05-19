#!/bin/bash
# WiFi Channel Hopping Service v2
# Aumentado tempo por canal para melhorar taxa de captura

INTERFACE="wlan1"
CHANNELS=(1 6 11)
DWELL_TIME=2  # segundos em cada canal (aumentado de 0.4)

while true; do
    for ch in "${CHANNELS[@]}"; do
        # Preferir 'iw dev' a 'iwconfig' (mais fiavel em modo monitor)
        if command -v iw >/dev/null 2>&1; then
            sudo iw dev "$INTERFACE" set channel "$ch" 2>/dev/null
        else
            sudo iwconfig "$INTERFACE" channel "$ch" 2>/dev/null
        fi
        sleep "$DWELL_TIME"
    done
done
