from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.dependencies import get_influx_service, get_savings_service
from app.core.settings import Settings, get_settings
from app.models.telemetry import HealthResponse, SavingsSummary, TelemetryPoint
from app.services.influx_service import InfluxTelemetryService
from app.services.savings_service import SavingsService

router = APIRouter()

# Global state memory for live simulator overlay.
current_env: dict[str, float] = {
    "indoor_temp": 21.5,
    "outdoor_temp": 15.0,
}

# Manual override flag -- when True the inference loop skips BACnet writes.
ai_override_active: bool = False

RATE_CAD_PER_KWH: float = 0.15


class EnvironmentUpdate(BaseModel):
    indoor_temp: float = Field(ge=-30.0, le=50.0)
    outdoor_temp: float = Field(ge=-50.0, le=60.0)


class OverrideUpdate(BaseModel):
    active: bool


def _generate_reasoning(indoor: float, outdoor: float, heating: float, cooling: float) -> str:
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


def _latest_setpoints_or_default(influx_service: InfluxTelemetryService) -> dict[str, float]:
    try:
        return influx_service.query_latest_setpoints()
    except Exception:
        return {"heating_setpoint": 20.0, "cooling_setpoint": 24.0}


@router.get("/health", response_model=HealthResponse, tags=["system"])
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
    )


@router.post("/environment", tags=["control"])
def update_environment(env: EnvironmentUpdate) -> dict[str, float]:
    global current_env
    current_env["indoor_temp"] = env.indoor_temp
    current_env["outdoor_temp"] = env.outdoor_temp
    return current_env


@router.get("/environment", tags=["control"])
def get_environment(
    influx_service: InfluxTelemetryService = Depends(get_influx_service),
) -> dict[str, Any]:
    indoor: float = current_env["indoor_temp"]
    outdoor: float = current_env["outdoor_temp"]
    setpoints = _latest_setpoints_or_default(influx_service)

    return {
        "indoor_temp": indoor,
        "outdoor_temp": outdoor,
        "recommendation_reason": _generate_reasoning(
            indoor=indoor,
            outdoor=outdoor,
            heating=setpoints["heating_setpoint"],
            cooling=setpoints["cooling_setpoint"],
        ),
    }


@router.post("/override", tags=["control"])
def set_override(payload: OverrideUpdate) -> dict[str, bool]:
    global ai_override_active
    ai_override_active = payload.active
    return {"override_active": ai_override_active}


@router.get("/override", tags=["control"])
def get_override() -> dict[str, bool]:
    return {"override_active": ai_override_active}


@router.get("/energy/project", tags=["analytics"])
def project_energy(
    settings: Settings = Depends(get_settings),
    influx_service: InfluxTelemetryService = Depends(get_influx_service),
) -> dict[str, float]:
    setpoints = _latest_setpoints_or_default(influx_service)
    heating_set: float = setpoints["heating_setpoint"]
    cooling_set: float = setpoints["cooling_setpoint"]
    indoor: float = current_env["indoor_temp"]
    outdoor: float = current_env["outdoor_temp"]

    if indoor < heating_set or indoor > cooling_set:
        projected_kwh = settings.baseline_hvac_kw + (abs(outdoor - indoor) * 1.2)
    else:
        projected_kwh = 2.5

    return {"projected_kwh": round(projected_kwh, 2)}


@router.get("/telemetry/latest", tags=["telemetry"])
def get_latest_telemetry(
    influx_service: InfluxTelemetryService = Depends(get_influx_service),
) -> list[dict[str, Any]]:
    try:
        return influx_service.query_recent_control_window(start="-1h", limit=5000)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Influx query failed: {exc}") from exc


@router.get("/telemetry/point/latest", response_model=TelemetryPoint, tags=["telemetry"])
def get_latest_telemetry_point(
    influx_service: InfluxTelemetryService = Depends(get_influx_service),
) -> TelemetryPoint:
    try:
        latest_point = influx_service.query_latest()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Influx query failed: {exc}") from exc

    if latest_point is None:
        raise HTTPException(status_code=404, detail="No telemetry data found.")
    return latest_point


@router.get("/telemetry/window", response_model=list[TelemetryPoint], tags=["telemetry"])
def get_telemetry_window(
    start: str = Query(default="-24h", description="Flux range start: -24h or ISO8601 UTC"),
    stop: str = Query(default="now()", description="Flux range stop: now() or ISO8601 UTC"),
    limit: int = Query(default=1000, ge=1, le=5000),
    descending: bool = Query(default=False),
    influx_service: InfluxTelemetryService = Depends(get_influx_service),
) -> list[TelemetryPoint]:
    try:
        return influx_service.query_window(start=start, stop=stop, limit=limit, descending=descending)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Influx query failed: {exc}") from exc


@router.get("/savings_summary", tags=["analytics"])
def get_savings_summary(
    settings: Settings = Depends(get_settings),
    influx_service: InfluxTelemetryService = Depends(get_influx_service),
) -> dict[str, float]:
    setpoints = _latest_setpoints_or_default(influx_service)
    heating_set: float = setpoints["heating_setpoint"]
    cooling_set: float = setpoints["cooling_setpoint"]
    indoor: float = current_env["indoor_temp"]
    outdoor: float = current_env["outdoor_temp"]

    baseline_kwh: float = settings.baseline_hvac_kw
    if indoor < heating_set or indoor > cooling_set:
        ai_kwh: float = settings.baseline_hvac_kw + (abs(outdoor - indoor) * 1.2)
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


@router.get("/savings/summary", response_model=SavingsSummary, tags=["savings"])
def get_detailed_savings_summary(
    start: str = Query(default="-24h", description="Flux range start: -24h or ISO8601 UTC"),
    stop: str = Query(default="now()", description="Flux range stop: now() or ISO8601 UTC"),
    limit: int = Query(default=2000, ge=1, le=10000),
    influx_service: InfluxTelemetryService = Depends(get_influx_service),
    savings_service: SavingsService = Depends(get_savings_service),
) -> SavingsSummary:
    try:
        telemetry_points = influx_service.query_window(start=start, stop=stop, limit=limit, descending=False)
        return savings_service.estimate_summary(telemetry_points)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Savings calculation failed: {exc}") from exc
