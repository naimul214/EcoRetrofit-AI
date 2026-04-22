from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for the FastAPI backend."""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "EcoRetrofit Backend API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"

    influx_url: str = Field(default="http://localhost:8086", validation_alias="INFLUXDB_URL")
    influx_token: str = Field(default="", validation_alias="INFLUXDB_ADMIN_TOKEN")
    influx_org: str = Field(default="ecoretrofit", validation_alias="INFLUXDB_ORG")
    influx_bucket: str = Field(default="ecoretrofit_telemetry", validation_alias="INFLUXDB_BUCKET")

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        validation_alias="CORS_ORIGINS",
    )

    # Ontario TOU electricity rates in CAD/kWh.
    tou_off_peak_cad_per_kwh: float = Field(default=0.087, validation_alias="TOU_OFF_PEAK_CAD_PER_KWH")
    tou_mid_peak_cad_per_kwh: float = Field(default=0.122, validation_alias="TOU_MID_PEAK_CAD_PER_KWH")
    tou_on_peak_cad_per_kwh: float = Field(default=0.182, validation_alias="TOU_ON_PEAK_CAD_PER_KWH")

    # Proxy energy model controls.
    baseline_hvac_kw: float = Field(default=12.0, validation_alias="BASELINE_HVAC_KW")
    baseline_deadband_c: float = Field(default=2.0, validation_alias="BASELINE_DEADBAND_C")
    min_power_factor: float = Field(default=0.55, validation_alias="MIN_POWER_FACTOR")
    max_power_factor: float = Field(default=1.15, validation_alias="MAX_POWER_FACTOR")
    fallback_interval_minutes: int = Field(default=5, validation_alias="FALLBACK_INTERVAL_MINUTES")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        """Allow list input or comma-delimited env string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            parsed: list[str] = []
            for origin in value:
                normalized = str(origin).strip()
                if normalized:
                    parsed.append(normalized)
            return parsed
        raise ValueError("CORS_ORIGINS must be a list or comma-delimited string.")


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached settings instance."""
    return Settings()
