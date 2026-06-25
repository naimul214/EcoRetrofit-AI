<div align="center">

#  EcoRetrofit AI

### AI-Driven Energy Optimization for Commercial Buildings

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-000000.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-gray.svg)](https://onnxruntime.ai/)

*A production-ready edge inference system that uses Reinforcement Learning (PPO) to autonomously optimize HVAC setpoints in commercial buildings, reducing energy consumption while maintaining thermal comfort.*

</div>

---

## Overview

EcoRetrofit AI trains a PPO agent inside the [Sinergym](https://github.com/ugr-sail/sinergym) building simulation environment and deploys the learned policy as a lightweight ONNX model to a Raspberry Pi 4 edge gateway. The Pi reads live environmental data, runs real-time inference (~8ms per decision), and broadcasts optimal heating/cooling setpoints to the building's HVAC system via BACnet protocol.

A live dashboard provides real-time visibility into the AI's decisions, energy savings, and system health.

### Key Features

- **Real-Time Edge AI** — ONNX inference running at ~8ms on Raspberry Pi 4 ARM64
- **BACnet Integration** — Direct communication with commercial HVAC controllers
- **Live Dashboard** — Next.js dashboard with real-time charts, AI reasoning, and system heartbeat
- **Manual Override** — One-click BACnet override switch for safety and demos
- **Telemetry Pipeline** — Full InfluxDB time-series logging with energy savings tracking
- **Graceful Lifecycle** — Signal handling, connection cleanup, and auto-restart via systemd

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Developer Workstation                        │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │  Next.js 16  │◄──►│  FastAPI     │◄──►│  InfluxDB 2.7         │  │
│  │  Dashboard   │    │  Backend     │    │  Telemetry Store      │  │
│  │  :3000       │    │  :8010       │    │  :8086                │  │
│  └──────────────┘    └──────▲───────┘    └───────────▲───────────┘  │
│                             │                        │              │
└─────────────────────────────┼────────────────────────┼──────────────┘
                              │  HTTP (env, override)  │  HTTP (write)
                              │                        │
┌─────────────────────────────┼────────────────────────┼──────────────┐
│                   Raspberry Pi 4 (Edge Gateway)      │              │
│                             │                        │              │
│  ┌──────────────────────────┴────────────────────────┴───────────┐  │
│  │                    local_inference.py                         │  │
│  │  1. Fetch env state ──► 2. Normalize obs ──► 3. ONNX infer    │  │
│  │  4. Log to InfluxDB ──► 5. Write BACnet setpoints             │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                             │  BACnet/IP (UDP 47808)                │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  HVAC Controller  │
                    │  (BACnet Device)  │
                    └───────────────────┘
```

---

## Project Structure

```
EcoRetrofit-AI/
├── src/
│   ├── edge/                        #    Edge inference (runs on Raspberry Pi)
│   │   ├── local_inference.py       #    Main inference loop
│   │   ├── bacnet_translator.py     #    BACnet write bridge
│   │   ├── database.py              #    InfluxDB telemetry logger
│   │   ├── models/                  #    ONNX model weights
│   │   │   └── ecoretrofit_3M.onnx  #    Trained PPO policy (3M steps)
│   │   ├── Dockerfile               #    Container definition
│   │   ├── docker-compose.yml       #    Full stack (InfluxDB + edge)
│   │   ├── requirements.txt         #    Pinned Python dependencies
│   │   └── .env.example             #    Environment variable template
│   │
│   ├── web/
│   │   ├── backend/                 #    FastAPI backend
│   │   │   ├── main.py              #    API server (env, telemetry, savings, override)
│   │   │   ├── requirements.txt     #    Backend dependencies
│   │   │   └── .env.example         #    Backend env template
│   │   │
│   │   └── frontend/               #     Next.js dashboard
│   │       └── src/app/
│   │           ├── page.tsx         #    Dashboard (charts, controls, heartbeat)
│   │           └── layout.tsx       #    Root layout with metadata
│   │
│   ├── training/                    #    Model training pipeline
│   │   ├── train_ppo.py             #    PPO training with Sinergym
│   │   ├── eval_ppo.py              #    Model evaluation loop
│   │   └── export_onnx.py           #    ONNX export script
│   │
│   └── simulation/                  #    Sinergym environment utilities
│       ├── noise_wrapper.py         #    Sensor noise injection wrapper
│       ├── rbc_agent.py             #    Rule-based baseline controller
│       └── generate_massive_dataset.py  # Domain randomization data generator
│
├── LICENSE
└── README.md
```

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend + Edge |
| Node.js | 20.9+ | Frontend dashboard |
| Docker | 24+ | InfluxDB + edge container |

### 1. Clone the Repository

```bash
git clone https://github.com/naimul214/EcoRetrofit-AI.git
cd EcoRetrofit-AI
```

### 2. Start InfluxDB

```bash
cd src/edge

# Linux/Mac
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env

# Edit .env with your credentials, then:
docker compose up -d influxdb
```

### 3. Start the FastAPI Backend

```bash
cd src/web/backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\Activate.ps1
# Activate (Linux/Mac)
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment

# Linux/Mac
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env

# Start the backend
python main.py
```

The backend will be running at `http://localhost:8010`.

### 4. Start the Next.js Dashboard

```bash
cd src/web/frontend

npm install

# Linux/Mac
cp .env.example .env.local

# Windows PowerShell
Copy-Item .env.example .env.local

npm run dev
```

Open `http://localhost:3000` in your browser.

### 5. Start the Edge Inference (Local or Pi)

**Option A: Run locally (for development)**

```bash
cd src/edge

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
python -u local_inference.py
```

**Option B: Run via Docker**

```bash
cd src/edge
docker build -t ecoretrofit-edge:local .
docker run --rm --env-file .env --network host ecoretrofit-edge:local
```

**Option C: Deploy to Raspberry Pi 4**

```bash
# From your development machine:
ssh pi@<PI_IP> "mkdir -p ~/ecoretrofit-edge/models"
scp src/edge/local_inference.py src/edge/database.py src/edge/bacnet_translator.py src/edge/requirements.txt pi@<PI_IP>:~/ecoretrofit-edge/
scp src/edge/models/ecoretrofit_3M.onnx pi@<PI_IP>:~/ecoretrofit-edge/models/

# SSH into the Pi:
ssh pi@<PI_IP>
cd ~/ecoretrofit-edge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create .env (replace YOUR_PC_IP with the IP of the machine running the backend)
cat > .env << 'EOF'
INFLUXDB_URL=http://YOUR_PC_IP:8086
INFLUXDB_ADMIN_TOKEN=your_token_here
INFLUXDB_ORG=ecoretrofit
INFLUXDB_BUCKET=ecoretrofit_telemetry
BACKEND_API_URL=http://YOUR_PC_IP:8010/api/environment
EOF

python -u local_inference.py
```

---

## Environment Variables

### Edge Service (`src/edge/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `INFLUXDB_URL` | InfluxDB endpoint | `http://192.168.5.39:8086` |
| `INFLUXDB_ADMIN_TOKEN` | InfluxDB auth token | `your_token_here` |
| `INFLUXDB_ORG` | InfluxDB organization | `ecoretrofit` |
| `INFLUXDB_BUCKET` | InfluxDB bucket name | `ecoretrofit_telemetry` |
| `BACKEND_API_URL` | FastAPI environment endpoint | `http://192.168.5.39:8010/api/environment` |

### Backend Service (`src/web/backend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `INFLUXDB_URL` | InfluxDB endpoint | `http://localhost:8086` |
| `INFLUXDB_ADMIN_TOKEN` | InfluxDB auth token | `your_token_here` |
| `INFLUXDB_ORG` | InfluxDB organization | `ecoretrofit` |
| `INFLUXDB_BUCKET` | InfluxDB bucket name | `ecoretrofit_telemetry` |
| `BASELINE_HVAC_KW` | Baseline HVAC load for savings calculation | `12.0` |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Service health and version |
| `GET` | `/api/environment` | Current temps + AI reasoning text |
| `POST` | `/api/environment` | Update simulated indoor/outdoor temps |
| `GET` | `/api/telemetry/latest` | Last hour of HVAC control data from InfluxDB |
| `GET` | `/api/telemetry/point/latest` | Latest structured telemetry point |
| `GET` | `/api/telemetry/window` | Windowed telemetry query |
| `GET` | `/api/energy/project` | Projected energy consumption (kWh) |
| `GET` | `/api/savings_summary` | Real-time energy and cost savings |
| `GET` | `/api/savings/summary` | Detailed TOU savings summary |
| `GET` | `/api/override` | Current manual override status |
| `POST` | `/api/override` | Toggle AI/manual BACnet control |

---

## Training Pipeline

The PPO agent was trained on the `Eplus-5zone-cool-discrete-v1` environment from Sinergym using Stable Baselines 3.

```bash
cd src/training
pip install -r requirements.txt

# Train (requires EnergyPlus and Sinergym)
python train_ppo.py

# Evaluate
python eval_ppo.py

# Export to ONNX for edge deployment
python export_onnx.py
```

Default training artifacts are saved to:

- `models/weights/ppo_discrete_ecoretrofit_5M.zip`
- `models/weights/vec_normalize_discrete.pkl`
- `models/weights/checkpoints/`

Optional overrides:

- `EVAL_MODEL_PATH=<path-to-model.zip>` for `eval_ppo.py`
- `PPO_MODEL_PATH=<path-to-model.zip>` for `export_onnx.py`

The trained model uses a 17-dimensional observation space and a discrete action space with 10 heating/cooling setpoint combinations derived from Sinergym's `DEFAULT_5ZONE_DISCRETE_FUNCTION`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Training | Stable Baselines 3, Sinergym, PyTorch |
| Edge Inference | ONNX Runtime, NumPy |
| HVAC Communication | BACpypes3 (BACnet/IP) |
| Telemetry Storage | InfluxDB 2.7 |
| Backend API | FastAPI, Uvicorn |
| Frontend | Next.js 16, React 19, Recharts, Tailwind CSS |
| Containerization | Docker |
| Edge Hardware | Raspberry Pi 4 (ARM64) |

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

**© 2026 Naimul Hassan**
