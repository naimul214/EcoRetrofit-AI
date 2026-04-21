# EcoRetrofit FastAPI Backend

Task 5.1 backend initialization for telemetry analytics and estimated cost savings.

## Features
- FastAPI app scaffold under `app/` with modular services.
- InfluxDB telemetry query endpoints for `hvac_control` measurement.
- Ontario TOU rate period mapping for cost calculation.
- Estimated CAD savings summary endpoint using a configurable proxy energy model.

## Quick Start
1. Create a virtual environment and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and adjust values as needed.
4. Start the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

## Endpoints
- `GET /` root status.
- `GET /api/v1/health` service health.
- `GET /api/v1/telemetry/latest` latest telemetry point.
- `GET /api/v1/telemetry/window` telemetry list for a time window.
- `GET /api/v1/savings/summary` estimated TOU savings for a window.
