from pathlib import Path
import sys

import pytest

BACKEND_PATH = Path(__file__).resolve().parents[1] / "src" / "web" / "backend"
sys.path.insert(0, str(BACKEND_PATH))

from app.services.influx_service import InfluxTelemetryService  # noqa: E402


def test_format_flux_time_accepts_relative_expression() -> None:
    assert InfluxTelemetryService._format_flux_time("-24h") == "-24h"


def test_format_flux_time_formats_iso8601_utc() -> None:
    formatted = InfluxTelemetryService._format_flux_time("2026-01-01T12:00:00Z")
    assert formatted == 'time(v: "2026-01-01T12:00:00Z")'


def test_format_flux_time_rejects_invalid_string() -> None:
    with pytest.raises(ValueError):
        InfluxTelemetryService._format_flux_time("not-a-time")
