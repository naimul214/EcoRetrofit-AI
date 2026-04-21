import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class TelemetryDB:
    def __init__(self):
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(dotenv_path=env_path)

        self.url = os.environ.get("INFLUXDB_URL")
        self.token = os.environ.get("INFLUXDB_ADMIN_TOKEN")
        self.org = os.environ.get("INFLUXDB_ORG")
        self.bucket = os.environ.get("INFLUXDB_BUCKET")

        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def log_step(self, indoor_temp: float, heating_setpoint: float, cooling_setpoint: float):
        point = (
            Point("hvac_control")
            .field("indoor_temp", float(indoor_temp))
            .field("heating_setpoint", float(heating_setpoint))
            .field("cooling_setpoint", float(cooling_setpoint))
        )
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        print(f"[DATABASE] Logged - Temp: {indoor_temp}C | Heating: {heating_setpoint}C | Cooling: {cooling_setpoint}C")

    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()

if __name__ == "__main__":
    print("[SYSTEM] Initializing InfluxDB Telemetry Connection...")
    db = TelemetryDB()
    
    print("[SYSTEM] Transmitting dummy HVAC parameters...")
    db.log_step(indoor_temp=21.5, heating_setpoint=20.0, cooling_setpoint=24.0)
    
    print("[SYSTEM] Telemetry successfully written to local InfluxDB bucket!")
