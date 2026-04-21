from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_influx_service, get_savings_service
from app.core.settings import Settings, get_settings
from app.models.telemetry import HealthResponse, SavingsSummary, TelemetryPoint
from app.services.influx_service import InfluxTelemetryService
from app.services.savings_service import SavingsService

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
    )


@router.get("/telemetry/latest", response_model=TelemetryPoint, tags=["telemetry"])
def get_latest_telemetry(
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


@router.get("/savings/summary", response_model=SavingsSummary, tags=["savings"])
def get_savings_summary(
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
