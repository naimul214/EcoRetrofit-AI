from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

BACKEND_PATH = Path(__file__).resolve().parents[1] / "src" / "web" / "backend"
sys.path.insert(0, str(BACKEND_PATH))

from app.models.telemetry import TelemetryPoint  # noqa: E402
from app.services.savings_service import EnergyModelConfig, SavingsService  # noqa: E402
from app.services.tou_pricing import TouPricingService  # noqa: E402


def test_savings_summary_estimation_is_non_negative() -> None:
    pricing_service = TouPricingService(
        off_peak_cad_per_kwh=0.08,
        mid_peak_cad_per_kwh=0.12,
        on_peak_cad_per_kwh=0.18,
        timezone_name="UTC",
    )
    model_config = EnergyModelConfig(
        baseline_hvac_kw=12.0,
        baseline_deadband_c=2.0,
        min_power_factor=0.55,
        max_power_factor=1.15,
        fallback_interval_minutes=5,
    )
    service = SavingsService(pricing_service=pricing_service, model_config=model_config)

    start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    points = [
        TelemetryPoint(
            timestamp=start,
            indoor_temp=21.0,
            heating_setpoint=19.0,
            cooling_setpoint=25.0,
        ),
        TelemetryPoint(
            timestamp=start + timedelta(minutes=15),
            indoor_temp=21.2,
            heating_setpoint=19.0,
            cooling_setpoint=25.0,
        ),
    ]

    summary = service.estimate_summary(points)

    assert summary.point_count == 2
    assert summary.estimated_baseline_energy_kwh > 0.0
    assert summary.estimated_ai_energy_kwh <= summary.estimated_baseline_energy_kwh
    assert summary.estimated_savings_cad >= 0.0
