import re
from datetime import datetime, timezone
from typing import Any

from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi

from app.models.telemetry import TelemetryPoint

_RELATIVE_TIME_PATTERN = re.compile(r"^-[0-9]+[smhdw]$")


class InfluxTelemetryService:
    """Reads HVAC telemetry points from InfluxDB."""

    def __init__(self, url: str, token: str, org: str, bucket: str) -> None:
        self._org = org
        self._bucket = bucket
        self._client = InfluxDBClient(url=url, token=token, org=org)
        self._query_api: QueryApi = self._client.query_api()

    @staticmethod
    def _format_flux_time(time_expression: str) -> str:
        normalized = time_expression.strip()
        if normalized == "now()":
            return normalized
        if _RELATIVE_TIME_PATTERN.match(normalized):
            return normalized

        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                "Time value must be now(), relative duration (e.g. -24h), or ISO8601 UTC timestamp."
            ) from exc

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        utc_value = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return f'time(v: "{utc_value}")'

    def query_window(
        self,
        start: str = "-24h",
        stop: str = "now()",
        limit: int = 1000,
        descending: bool = False,
    ) -> list[TelemetryPoint]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        start_flux = self._format_flux_time(start)
        stop_flux = self._format_flux_time(stop)

        flux_query = f'''
from(bucket: "{self._bucket}")
  |> range(start: {start_flux}, stop: {stop_flux})
  |> filter(fn: (r) => r._measurement == "hvac_control")
  |> filter(fn: (r) => r._field == "indoor_temp" or r._field == "heating_setpoint" or r._field == "cooling_setpoint")
  |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
  |> keep(columns: ["_time", "indoor_temp", "heating_setpoint", "cooling_setpoint"])
  |> sort(columns: ["_time"], desc: {str(descending).lower()})
  |> limit(n: {limit})
'''

        tables = self._query_api.query(query=flux_query, org=self._org)

        points: list[TelemetryPoint] = []
        for table in tables:
            for record in table.records:
                values: dict[str, Any] = record.values
                indoor_temp = values.get("indoor_temp")
                heating_setpoint = values.get("heating_setpoint")
                cooling_setpoint = values.get("cooling_setpoint")
                timestamp = record.get_time()

                if timestamp is None:
                    continue
                if indoor_temp is None or heating_setpoint is None or cooling_setpoint is None:
                    continue

                points.append(
                    TelemetryPoint(
                        timestamp=timestamp,
                        indoor_temp=float(indoor_temp),
                        heating_setpoint=float(heating_setpoint),
                        cooling_setpoint=float(cooling_setpoint),
                    )
                )

        return points

    def query_latest(self) -> TelemetryPoint | None:
        points = self.query_window(start="-7d", stop="now()", limit=1, descending=True)
        if not points:
            return None
        return points[0]

    def close(self) -> None:
        self._client.close()
