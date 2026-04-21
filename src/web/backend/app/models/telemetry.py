from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app_name: str
    app_version: str


class TelemetryPoint(BaseModel):
    timestamp: datetime = Field(description="UTC timestamp for the telemetry sample.")
    indoor_temp: float
    heating_setpoint: float
    cooling_setpoint: float


class CostBreakdown(BaseModel):
    off_peak_cad: float
    mid_peak_cad: float
    on_peak_cad: float


class SavingsSummary(BaseModel):
    point_count: int
    estimated_ai_energy_kwh: float
    estimated_baseline_energy_kwh: float
    estimated_ai_cost_cad: float
    estimated_baseline_cost_cad: float
    estimated_savings_cad: float
    estimated_savings_percent: float
    cost_breakdown_ai: CostBreakdown
    cost_breakdown_baseline: CostBreakdown
