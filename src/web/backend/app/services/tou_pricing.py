from datetime import date, datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TouPeriod = Literal["off_peak", "mid_peak", "on_peak"]


class TouPricingService:
    """Calculates Ontario TOU pricing period and corresponding rate."""

    def __init__(
        self,
        off_peak_cad_per_kwh: float,
        mid_peak_cad_per_kwh: float,
        on_peak_cad_per_kwh: float,
        timezone_name: str = "America/Toronto",
    ) -> None:
        self._off_peak = off_peak_cad_per_kwh
        self._mid_peak = mid_peak_cad_per_kwh
        self._on_peak = on_peak_cad_per_kwh
        try:
            self._timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            self._timezone = timezone.utc

    @staticmethod
    def _is_summer(day: date) -> bool:
        return 5 <= day.month <= 10

    def period_for_timestamp(self, timestamp_utc: datetime) -> TouPeriod:
        local_time = timestamp_utc.astimezone(self._timezone)

        # Weekends are always off-peak for standard Ontario TOU.
        if local_time.weekday() >= 5:
            return "off_peak"

        hour = local_time.hour + (local_time.minute / 60.0)
        if self._is_summer(local_time.date()):
            if 11.0 <= hour < 17.0:
                return "on_peak"
            if 7.0 <= hour < 11.0 or 17.0 <= hour < 19.0:
                return "mid_peak"
            return "off_peak"

        if 7.0 <= hour < 11.0 or 17.0 <= hour < 19.0:
            return "on_peak"
        if 11.0 <= hour < 17.0:
            return "mid_peak"
        return "off_peak"

    def rate_for_period(self, period: TouPeriod) -> float:
        if period == "on_peak":
            return self._on_peak
        if period == "mid_peak":
            return self._mid_peak
        return self._off_peak
