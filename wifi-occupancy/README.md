# WiFi Occupancy - Biblioteca

Sistema de monitorizacao de ocupacao via WiFi probe requests.

## Estrutura

```
wifi-occupancy/
├── capture.sh          # Captura tshark (modo monitor)
├── channel-hop.sh      # Channel hopping 1-6-11
├── process.py          # Pipeline: pcap -> SQLite
├── dashboard.py        # Streamlit UI
├── install.sh          # Setup automatico
├── data/
│   ├── raw/            # Ficheiros pcap
│   ├── db/             # SQLite (occupancy.db)
│   └── model/          # Modelo treinado (JSON)
├── logs/               # Logs dos servicos
└── services/           # Ficheiros systemd
```

## Instalacao Rapida

```bash
cd /home/islab/wifi-occupancy
./install.sh
```

## Comandos Uteis

```bash
# Ver estado dos servicos
sudo systemctl status wifi-capture
sudo systemctl status wifi-channel-hop
sudo systemctl status wifi-dashboard

# Ver logs
tail -f /home/islab/wifi-occupancy/logs/*.log

# Processar manualmente
python3 /home/islab/wifi-occupancy/process.py

# Dashboard manual
streamlit run /home/islab/wifi-occupancy/dashboard.py --server.port 8501
```

## Acesso

- Dashboard: `http://IP-DO-PI:8501`
- Dados: SQLite em `data/db/occupancy.db`
