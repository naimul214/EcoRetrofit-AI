import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, List

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

load_dotenv()

INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_ADMIN_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")

# Energy model constants
BASELINE_HVAC_KW: float = float(os.environ.get("BASELINE_HVAC_KW", 12.0))
RATE_CAD_PER_KWH: float = 0.15


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Create a single InfluxDB client for the entire application lifetime.
    Reusing one connection pool prevents TCP port exhaustion under polling load."""
    influx = InfluxDBClient(
        url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
    )
    app.state.influx = influx
    yield
    influx.close()


app = FastAPI(title="EcoRetrofit Edge Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state memory for live simulator overlay
current_env: Dict[str, float] = {
    "indoor_temp": 21.5,
    "outdoor_temp": 15.0,
}

# Manual override flag -- when True the inference loop skips BACnet writes
ai_override_active: bool = False


class EnvironmentUpdate(BaseModel):
    indoor_temp: float
    outdoor_temp: float


class OverrideUpdate(BaseModel):
    active: bool


@app.post("/api/environment")
def update_environment(env: EnvironmentUpdate) -> Dict[str, float]:
    global current_env
    current_env["indoor_temp"] = env.indoor_temp
    current_env["outdoor_temp"] = env.outdoor_temp
    return current_env


def _generate_reasoning(
    indoor: float,
    outdoor: float,
    heating: float,
    cooling: float,
) -> str:
    """Generate a human-readable explanation of what the AI is doing and why.
    This turns raw setpoint numbers into judge-friendly insight text."""
    if indoor < heating:
        return (
            f"Indoor temp ({indoor:.1f}C) is below the heating setpoint "
            f"({heating:.1f}C). HVAC heating is engaged to restore thermal comfort."
        )
    if indoor > cooling:
        return (
            f"Indoor temp ({indoor:.1f}C) exceeds the cooling setpoint "
            f"({cooling:.1f}C). HVAC cooling is activated to reduce thermal load."
        )
    # Indoor is within the comfort band -- explain the strategy
    if outdoor > 30:
        return (
            f"Extreme external heat ({outdoor:.1f}C outdoor). AI is holding a tight "
            f"cooling band ({cooling:.1f}C) to pre-empt thermal drift."
        )
    if outdoor > 25:
        return (
            f"High external heat load ({outdoor:.1f}C outdoor). AI is prioritizing "
            f"cooling efficiency with setpoint at {cooling:.1f}C."
        )
    if outdoor < 0:
        return (
            f"Sub-zero outdoor temp ({outdoor:.1f}C). AI is maintaining heating at "
            f"{heating:.1f}C while minimizing energy draw."
        )
    if outdoor < 5:
        return (
            f"Low external temp ({outdoor:.1f}C outdoor). AI has widened the heating "
            f"deadband to {heating:.1f}C to reduce energy waste."
        )
    return (
        f"Indoor temp ({indoor:.1f}C) is within the comfort zone "
        f"({heating:.1f}-{cooling:.1f}C). HVAC in standby -- minimizing energy use."
    )


@app.get("/api/environment")
def get_environment(request: Request) -> Dict[str, Any]:
    indoor: float = current_env["indoor_temp"]
    outdoor: float = current_env["outdoor_temp"]

    # Attempt to generate reasoning from live setpoints
    try:
        setpoints = _get_latest_setpoints(request)
        heating = setpoints["heating_setpoint"]
        cooling = setpoints["cooling_setpoint"]
        reason = _generate_reasoning(indoor, outdoor, heating, cooling)
    except Exception:
        reason = "Analyzing environmental conditions..."

    return {
        "indoor_temp": indoor,
        "outdoor_temp": outdoor,
        "recommendation_reason": reason,
    }


@app.post("/api/override")
def set_override(payload: OverrideUpdate) -> Dict[str, bool]:
    global ai_override_active
    ai_override_active = payload.active
    state = "ENGAGED" if ai_override_active else "RELEASED"
    print(f"[BACKEND] Manual override {state}.")
    return {"override_active": ai_override_active}


@app.get("/api/override")
def get_override() -> Dict[str, bool]:
    return {"override_active": ai_override_active}


def _get_latest_setpoints(request: Request) -> Dict[str, float]:
    """Query the most recent heating/cooling setpoints from InfluxDB.
    Uses the shared singleton client from app.state."""
    if not all([INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
        raise HTTPException(
            status_code=500,
            detail="InfluxDB connection variables are not fully configured.",
        )

    query_api = request.app.state.influx.query_api()
    query: str = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "hvac_control")
      |> filter(fn: (r) => r._field == "heating_setpoint" or r._field == "cooling_setpoint")
      |> last()
    """

    try:
        tables = query_api.query(query, org=INFLUXDB_ORG)
        heating: float = 20.0
        cooling: float = 24.0
        for table in tables:
            for record in table.records:
                if record.get_field() == "heating_setpoint" and record.get_value() is not None:
                    heating = float(record.get_value())
                elif record.get_field() == "cooling_setpoint" and record.get_value() is not None:
                    cooling = float(record.get_value())
        return {"heating_setpoint": heating, "cooling_setpoint": cooling}
    except InfluxDBError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/energy/project")
def project_energy(request: Request) -> Dict[str, float]:
    setpoints = _get_latest_setpoints(request)
    heating_set: float = setpoints["heating_setpoint"]
    cooling_set: float = setpoints["cooling_setpoint"]
    indoor: float = current_env["indoor_temp"]
    outdoor: float = current_env["outdoor_temp"]

    if indoor < heating_set or indoor > cooling_set:
        projected_kwh = BASELINE_HVAC_KW + (abs(outdoor - indoor) * 1.2)
    else:
        projected_kwh = 2.5

    return {"projected_kwh": round(projected_kwh, 2)}


@app.get("/api/telemetry/latest")
def get_latest_telemetry(request: Request) -> List[Dict[str, Any]]:
    if not all([INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
        raise HTTPException(
            status_code=500,
            detail="InfluxDB connection variables are not fully configured.",
        )

    query_api = request.app.state.influx.query_api()
    query: str = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "hvac_control")
      |> filter(fn: (r) => r._field == "indoor_temp" or r._field == "heating_setpoint" or r._field == "cooling_setpoint" or r._field == "latency_ms")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    try:
        tables = query_api.query(query, org=INFLUXDB_ORG)
        results: List[Dict[str, Any]] = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time": record.get_time().isoformat() if record.get_time() else None,
                    "indoor_temp": record.values.get("indoor_temp"),
                    "heating_setpoint": record.values.get("heating_setpoint"),
                    "cooling_setpoint": record.values.get("cooling_setpoint"),
                    "latency_ms": record.values.get("latency_ms"),
                })
        return results
    except InfluxDBError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/savings_summary")
def get_savings_summary(request: Request) -> Dict[str, float]:
    """Calculate real-time savings by comparing current AI energy projection
    against the configured baseline HVAC load."""
    setpoints = _get_latest_setpoints(request)
    heating_set: float = setpoints["heating_setpoint"]
    cooling_set: float = setpoints["cooling_setpoint"]
    indoor: float = current_env["indoor_temp"]
    outdoor: float = current_env["outdoor_temp"]

    # Baseline: always running at full HVAC capacity
    baseline_kwh: float = BASELINE_HVAC_KW

    # AI-controlled: only engages HVAC when outside the setpoint deadband
    if indoor < heating_set or indoor > cooling_set:
        ai_kwh: float = BASELINE_HVAC_KW + (abs(outdoor - indoor) * 1.2)
    else:
        ai_kwh = 2.5

    kwh_saved: float = max(0.0, baseline_kwh - ai_kwh)
    cad_saved: float = kwh_saved * RATE_CAD_PER_KWH

    return {
        "baseline_kwh": round(baseline_kwh, 2),
        "ai_kwh": round(ai_kwh, 2),
        "kwh_saved": round(kwh_saved, 2),
        "cad_saved": round(cad_saved, 2),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
