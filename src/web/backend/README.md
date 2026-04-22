# EcoRetrofit FastAPI Backend

Unified backend API for edge control, telemetry, and savings analytics.

## Features
- Single canonical API contract under `/api`.
- Live simulator environment + manual override endpoints for edge integration.
- InfluxDB telemetry endpoints for both dashboard feed and analytical windows.
- Ontario TOU pricing and estimated savings analytics.

## Quick Start
1. Create a virtual environment and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and adjust values as needed.
4. Start the API:

```bash
python main.py
```

Alternative launcher:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

## Endpoints
- `GET /` root status.
- `GET /api/health` service health.
- `GET /api/environment` current indoor/outdoor environment with AI reasoning.
- `POST /api/environment` update indoor/outdoor simulator overlay.
- `GET /api/override` current manual override state.
- `POST /api/override` toggle manual override state.
- `GET /api/telemetry/latest` dashboard feed (last hour list with setpoints + latency).
- `GET /api/telemetry/window` analytical telemetry window.
- `GET /api/telemetry/point/latest` latest structured telemetry sample.
- `GET /api/energy/project` projected energy estimate.
- `GET /api/savings_summary` simple real-time savings summary.
- `GET /api/savings/summary` detailed TOU savings summary.
