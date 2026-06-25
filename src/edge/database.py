"""
Database service for telemetry collection.
Handles writing HVAC metrics to InfluxDB.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

logger: logging.Logger = logging.getLogger("TelemetryDB")


class TelemetryDB:
    def __init__(self) -> None:
        # Load .env from disk only if it exists (native Pi run).
        # Inside Docker, env vars are injected via --env-file and this is skipped.
        # override=False ensures Docker-injected vars always take precedence.
        env_path: Path = Path(__file__).resolve().parent / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=str(env_path), override=False)

        self.url: str = os.environ.get("INFLUXDB_URL", "")
        self.token: str = os.environ.get("INFLUXDB_ADMIN_TOKEN", "")
        self.org: str = os.environ.get("INFLUXDB_ORG", "")
        self.bucket: str = os.environ.get("INFLUXDB_BUCKET", "")

        self.client: InfluxDBClient = InfluxDBClient(url=self.url, token=self.token, org=self.org)
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
        point: Point = (
            Point("hvac_control")
            .field("indoor_temp", float(indoor_temp))
            .field("heating_setpoint", float(heating_setpoint))
            .field("cooling_setpoint", float(cooling_setpoint))
            .field("latency_ms", float(latency_ms))
        )
        try:
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info(
                "Logged control step - Temp: %sC | Heating: %sC | Cooling: %sC | Latency: %.2fms",
                indoor_temp,
                heating_setpoint,
                cooling_setpoint,
                latency_ms,
                extra={
                    "indoor_temp": indoor_temp,
                    "heating_setpoint": heating_setpoint,
                    "cooling_setpoint": cooling_setpoint,
                    "latency_ms": latency_ms,
                }
            )
        except InfluxDBError as e:
            logger.warning("InfluxDB write failed, telemetry skipped: %s", e)
        except Exception as e:
            logger.warning("Unexpected write failure, telemetry skipped: %s", e)

    def close(self) -> None:
        """Explicitly close the InfluxDB connection and flush write buffers."""
        self.client.close()

    def __del__(self) -> None:
        if hasattr(self, 'client'):
            self.client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger.info("Initializing InfluxDB Telemetry Connection...")
    db: TelemetryDB = TelemetryDB()
    logger.info("Transmitting dummy HVAC parameters...")
    db.log_step(indoor_temp=21.5, heating_setpoint=20.0, cooling_setpoint=24.0, latency_ms=5.0)
    db.close()
    logger.info("Telemetry successfully written to local InfluxDB bucket!")
