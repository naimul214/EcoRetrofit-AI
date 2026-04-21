import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

load_dotenv()

app = FastAPI(title="EcoRetrofit Edge Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_ADMIN_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")

# Global state memory for live simulator overlay
current_env: Dict[str, float] = {
    "indoor_temp": 21.5,
    "outdoor_temp": 15.0
}

class EnvironmentUpdate(BaseModel):
    indoor_temp: float
    outdoor_temp: float

@app.post("/api/environment")
def update_environment(env: EnvironmentUpdate) -> Dict[str, float]:
    global current_env
    current_env["indoor_temp"] = env.indoor_temp
    current_env["outdoor_temp"] = env.outdoor_temp
    return current_env

@app.get("/api/environment")
def get_environment() -> Dict[str, float]:
    return current_env

def _get_latest_setpoints() -> Dict[str, float]:
    if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
        raise HTTPException(status_code=500, detail="InfluxDB connection variables are not fully configured.")

    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()

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

        return {
            "heating_setpoint": heating,
            "cooling_setpoint": cooling
        }
    except InfluxDBError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()

@app.get("/api/energy/project")
def project_energy() -> Dict[str, float]:
    setpoints = _get_latest_setpoints()
    heating_set: float = setpoints["heating_setpoint"]
    cooling_set: float = setpoints["cooling_setpoint"]
    
    indoor: float = current_env["indoor_temp"]
    outdoor: float = current_env["outdoor_temp"]

    if indoor < heating_set or indoor > cooling_set:
        projected_kwh = 15.0 + (abs(outdoor - indoor) * 1.2)
    else:
        projected_kwh = 2.5
        
    return {"projected_kwh": round(projected_kwh, 2)}

@app.get("/api/telemetry/latest")
def get_latest_telemetry() -> List[Dict[str, Any]]:
    if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
        raise HTTPException(status_code=500, detail="InfluxDB connection variables are not fully configured.")

    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()

    query: str = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "hvac_control")
      |> filter(fn: (r) => r._field == "indoor_temp" or r._field == "heating_setpoint" or r._field == "cooling_setpoint")
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
                })
        return results
    except InfluxDBError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()

@app.get("/api/savings_summary")
def get_savings_summary() -> Dict[str, float]:
    baseline_kwh: float = 32.2
    ai_kwh: float = 24.8
    rate_per_kwh: float = 0.15

    kwh_saved: float = baseline_kwh - ai_kwh
    cad_saved: float = kwh_saved * rate_per_kwh

    return {
        "baseline_kwh": round(baseline_kwh, 2),
        "ai_kwh": round(ai_kwh, 2),
        "kwh_saved": round(kwh_saved, 2),
        "cad_saved": round(cad_saved, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
