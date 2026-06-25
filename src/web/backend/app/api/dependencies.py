from functools import lru_cache

from app.core.settings import get_settings
from app.services.influx_service import InfluxTelemetryService
from app.services.savings_service import EnergyModelConfig, SavingsService
from app.services.state_service import StateService
from app.services.tou_pricing import TouPricingService


@lru_cache
def get_state_service() -> StateService:
    settings = get_settings()
    return StateService(db_path=settings.resolved_state_db_path)


@lru_cache
def get_influx_service() -> InfluxTelemetryService:
    settings = get_settings()
    return InfluxTelemetryService(
        url=settings.influx_url,
        token=settings.influx_token,
        org=settings.influx_org,
        bucket=settings.influx_bucket,
    )


@lru_cache
def get_tou_pricing_service() -> TouPricingService:
    settings = get_settings()
    return TouPricingService(
        off_peak_cad_per_kwh=settings.tou_off_peak_cad_per_kwh,
        mid_peak_cad_per_kwh=settings.tou_mid_peak_cad_per_kwh,
        on_peak_cad_per_kwh=settings.tou_on_peak_cad_per_kwh,
    )


@lru_cache
def get_savings_service() -> SavingsService:
    settings = get_settings()
    config = EnergyModelConfig(
        baseline_hvac_kw=settings.baseline_hvac_kw,
        baseline_deadband_c=settings.baseline_deadband_c,
        min_power_factor=settings.min_power_factor,
        max_power_factor=settings.max_power_factor,
        fallback_interval_minutes=settings.fallback_interval_minutes,
    )
    return SavingsService(pricing_service=get_tou_pricing_service(), model_config=config)
