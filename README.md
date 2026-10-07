# Environmental Sensing for Occupancy Estimation

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-CNN-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![scikit--learn](https://img.shields.io/badge/scikit--learn-clustering-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Flask](https://img.shields.io/badge/Flask-REST%20API-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-storage-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

Course project for **Sensorização e Ambiente** in the **Master's Degree in Artificial Intelligence at the University of Minho (UMinho)**.

## Problem and solution

Estimating how many people are using a room without collecting images is difficult: Wi-Fi probe traffic is noisy, devices randomise their MAC addresses, and one person may carry several devices. This repository evaluates complementary sensing strategies for the **Fernão Mendes Pinto Library (BGUM, Gualtar campus)**:

- passive Wi-Fi probe requests, filtered by RSSI and SSID and aggregated into 15-minute windows;
- device-count estimation with OPTICS clustering;
- CSI amplitude processing and a convolutional neural network for room/activity classes.

The result is a privacy-aware experimental stack that stores derived metrics rather than camera footage, exposes occupancy trends in a dashboard, and keeps the capture, processing and learning stages independently testable.

## Features and technical architecture

### Wi-Fi occupancy pipeline (`wifi-occupancy/`)

```text
Monitor-mode adapter (wlan1)
        │
        ▼
tshark probe-request capture ──► PCAP files in data/raw/
        │
        ▼
process.py
  ├─ RSSI >= -65 dBm and SSID filtering
  ├─ partial MAC anonymisation
  ├─ six engineered features per 15-minute window
  ├─ OPTICS device estimate
  └─ KMeans occupancy model selected by silhouette score
        │
        ▼
SQLite (occupancy.db) ──► Streamlit + Plotly dashboard
```

The dashboard reports the current occupancy label (`Vazia`, `Pouca Gente`, `Média`, `Cheia`, or `Muito Cheia`), probe count, unique MACs, RSSI statistics and the OPTICS estimate. It also provides time-series, daily statistics and a day/hour heatmap. The included `systemd` units schedule capture, processing and dashboard startup on a Linux/Raspberry Pi deployment.

### Remote ingestion and OPTICS (`optics_counter/`)

`edge_stream.py` captures probe requests from `wlan1`, hashes MAC addresses with SHA-256 and sends batches of 50 records to the Flask `/ingest` endpoint. `server_api.py` persists the records in `data/raw_packets.db`; `heavy_lifter.py` reads a rolling five-minute window, estimates devices with OPTICS and writes results to `data/device_counts.db`.

### CSI-based crowd counting (`crowd_counting_macless/`)

This offline pipeline:

1. reads Intel CSI binary files from `data/Room*/`;
2. extracts CSI amplitude with `csiread`;
3. applies a low-pass filter, normalises the signal and creates valid sliding windows;
4. trains a PyTorch CNN with a 70/15/15 train/validation/test split;
5. saves the best checkpoint as `models/cnn_weights_best.pt`.

The CSI dataset and generated arrays are not committed to this repository. See [`crowd_counting_macless/data/README.md`](crowd_counting_macless/data/README.md) for the dataset prerequisite.

## Installation and usage

The operational Wi-Fi components target **Linux with a monitor-mode-capable Wi-Fi adapter**, `tshark`, `iw` and `systemd`. The CSI experiment can run on a regular Python environment, with an optional CUDA installation for PyTorch.

### 1. Wi-Fi occupancy: Raspberry Pi/Linux deployment

The provided installer uses `/var/wifi-occupancy` as its deployment directory. Run it from a checkout copied to that location:

```bash
sudo cp -a wifi-occupancy /var/wifi-occupancy
cd /var/wifi-occupancy
sudo apt update
sudo apt install -y tshark iw python3-pip
sudo ./install.sh
```

The scripts expect the capture adapter to be named `wlan1`. Put it in monitor mode and start the services:

```bash
sudo ip link set wlan1 down
sudo iw dev wlan1 set type monitor
sudo ip link set wlan1 up

sudo systemctl start wifi-channel-hop
sudo systemctl start wifi-capture
sudo systemctl start wifi-process.timer
sudo systemctl start wifi-dashboard
```

Open `http://<raspberry-pi-ip>:8501`. The pipeline writes PCAP files, the SQLite database and logs below `/var/wifi-occupancy/data/` and `/var/wifi-occupancy/logs/`. To inspect the deployment:

```bash
sudo systemctl status wifi-capture wifi-process.timer wifi-dashboard
tail -f /var/wifi-occupancy/logs/*.log
python3 /var/wifi-occupancy/process.py
```

For a single-command startup after installation, use:

```bash
sudo /var/wifi-occupancy/quickstart.sh
```

To use a different interface, update `INTERFACE` in `capture.sh`, `channel-hop.sh` and the relevant systemd configuration before starting the services. `process.py` and `dashboard.py` currently use absolute paths under `/var/wifi-occupancy`; they are intended for this deployment layout.

### 2. Remote edge/server experiment

Install the Python dependencies on the edge device and server:

```bash
python3 -m pip install requests flask pandas scikit-learn
```

On the server, from `optics_counter/server/`, start the API:

```bash
python3 server_api.py
```

On the edge device, set `BACKEND_URL` and `INTERFACE` in `optics_counter/edge_stream.py`, then run:

```bash
python3 edge_stream.py
```

In a second server process, run the rolling OPTICS worker:

```bash
python3 heavy_lifter.py
```

The API listens on port `5000` and accepts JSON batches at `POST /ingest`. The edge and server must be able to reach one another, and `tshark` must be installed on the edge device.

### 3. CSI CNN experiment

From the CSI source directory, install the dependencies:

```bash
cd crowd_counting_macless
python3 -m pip install numpy scipy csiread torch
```

Place CSI files in directories matching `data/Room*/` and use filenames such as `1p.bin`, `2p.bin`, etc. Then run the pipeline from `src/` so that the relative paths in the scripts resolve correctly:

```bash
cd src
python3 data_parser.py
python3 preprocess.py
python3 train.py
```

`data_parser.py` creates `data/parsed/X_raw.npy` and `y_raw.npy`; `preprocess.py` creates `data/processed/X_train_ready.npy` and `y_train_ready.npy`; `train.py` writes the best model to `models/cnn_weights_best.pt` and evaluates it on the held-out split.

## Repository layout

```text
.
├── wifi-occupancy/              # Local Wi-Fi capture, processing and dashboard
├── optics_counter/              # Remote Flask ingestion and OPTICS worker
├── crowd_counting_macless/      # CSI parsing, preprocessing and CNN training
├── demo.png                     # Room/deployment illustration
├── SA2026_paper_8264.pdf        # Related paper submission
└── uji_probes.pdf               # UJI probe dataset reference
```

## Authorship

Developed collaboratively as an academic project for the **Sensorização e Ambiente** course of the **Master's Degree in Artificial Intelligence at UMinho**. The repository contains the team's sensing, data-processing and machine-learning prototypes developed for the course.
