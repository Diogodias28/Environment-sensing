#!/bin/bash
# WiFi Channel Hopping Service

INTERFACE="wlan1"

#while true; do
#    for ch in 1 6 11; do
#        sudo iwconfig "$INTERFACE" channel $ch 2>/dev/null || sudo iw dev "$INTERFACE" set channel $ch 2>/dev/null
#        sleep 0.4
#    done
#done

# channel-hop-dual.sh - 2.4 GHz + 5 GHz UNII-1 + UNII-3

#INTERFACE="wlan1"

#while true; do
    # 2.4 GHz (todos os canais)
#    for ch in $(seq 1 13); do
#        sudo iw dev $INTERFACE set channel $ch 2>/dev/null
#        sleep 0.1
#    done
    
#    # 5 GHz UNII-1 (sem radar)
#    for ch in 36 40 44 48; do
#        sudo iw dev $INTERFACE set channel $ch 2>/dev/null
#        sleep 0.1
#    done
    
    # 5 GHz UNII-3 (sem radar)
#    for ch in 149 153 157 161; do
#        sudo iw dev $INTERFACE set channel $ch 2>/dev/null
#        sleep 0.1
#    done
#done

#claude version
# Channel hopper - scan all 13 channe
while true; do
    for ch in 1 2 3 4 5 6 7 8 9 10 11 12 13; do
        sudo iw dev "$INTERFACE" set channel $ch 2>/dev/null
        sleep 0.2
    done
done
