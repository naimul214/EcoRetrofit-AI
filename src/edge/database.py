import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


class TelemetryDB:
    def __init__(self) -> None:
        # Load .env from disk only if it exists (native Pi run).
        # Inside Docker, env vars are injected via --env-file and this is skipped.
        # override=False ensures Docker-injected vars always take precedence.
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=False)

        self.url: str = os.environ.get("INFLUXDB_URL", "")
        self.token: str = os.environ.get("INFLUXDB_ADMIN_TOKEN", "")
        self.org: str = os.environ.get("INFLUXDB_ORG", "")
        self.bucket: str = os.environ.get("INFLUXDB_BUCKET", "")

        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def log_step(
        self,
        indoor_temp: float,
        heating_setpoint: float,
        cooling_setpoint: float,
        latency_ms: float = 0.0,
    ) -> None:
        """Write one HVAC control cycle to InfluxDB. Errors are logged but
        do not crash the inference loop."""
        point = (
            Point("hvac_control")
            .field("indoor_temp", float(indoor_temp))
            .field("heating_setpoint", float(heating_setpoint))
            .field("cooling_setpoint", float(cooling_setpoint))
            .field("latency_ms", float(latency_ms))
        )
        try:
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            print(
                f"[DATABASE] Logged - Temp: {indoor_temp}C | "
                f"Heating: {heating_setpoint}C | Cooling: {cooling_setpoint}C | "
                f"Latency: {latency_ms:.2f}ms"
            )
        except Exception as e:
            print(f"[DATABASE WARNING] Write failed, telemetry skipped: {e}")

    def close(self) -> None:
        """Explicitly close the InfluxDB connection and flush write buffers."""
        self.client.close()

    def __del__(self) -> None:
        if hasattr(self, 'client'):
            self.client.close()


if __name__ == "__main__":
    print("[SYSTEM] Initializing InfluxDB Telemetry Connection...")
    db = TelemetryDB()
    print("[SYSTEM] Transmitting dummy HVAC parameters...")
    db.log_step(indoor_temp=21.5, heating_setpoint=20.0, cooling_setpoint=24.0, latency_ms=5.0)
    db.close()
    print("[SYSTEM] Telemetry successfully written to local InfluxDB bucket!")
