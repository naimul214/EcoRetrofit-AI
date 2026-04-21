import asyncio
import requests
from typing import Dict
from bacpypes3.apdu import AbortPDU
from database import TelemetryDB
from bacnet_translator import BACnetBridge

async def run_inference_loop() -> None:
    print("[SYSTEM] Booting Edge Control Inference Sequence...")
    
    db = TelemetryDB()
    bridge = BACnetBridge()
    dummy_device: str = "192.168.5.24"
    object_identifier: str = "analogValue:1"

    cycle: int = 1
    while True:
        print(f"\n--- Inference Cycle {cycle} ---")
        
        try:
            response = requests.get("http://localhost:8010/api/environment", timeout=2)
            response.raise_for_status()
            env_data: Dict[str, float] = response.json()
            indoor_temp: float = float(env_data.get("indoor_temp", 21.5))
            outdoor_temp: float = float(env_data.get("outdoor_temp", 15.0))
        except Exception as e:
            print(f"[SYSTEM WARNING] Backend unreachable, defaulting telemetry memory: {e}")
            indoor_temp = 21.5
            outdoor_temp = 15.0

        # Reactive AI decision block
        if indoor_temp > 23.0:
            heating_setpoint: float = 18.0
            cooling_setpoint: float = 22.0
        elif indoor_temp < 19.0:
            heating_setpoint = 22.0
            cooling_setpoint = 26.0
        else:
            heating_setpoint = 20.0
            cooling_setpoint = 24.0
            
        print("[AI] Optimal Control Setpoints Generated.")
        
        # 1. Telemetry logging
        db.log_step(
            indoor_temp=indoor_temp, 
            heating_setpoint=heating_setpoint, 
            cooling_setpoint=cooling_setpoint
        )
        
        # 2. BACnet Translation
        try:
            print("[BACNET] Bridging parameters to physical hardware...")
            await bridge.write_setpoint(
                device_address=dummy_device, 
                object_identifier=object_identifier, 
                value=heating_setpoint
            )
        except AbortPDU as e:
            print(f"[NETWORK WARNING] BACnet Abort Exception Caught: {e}")
        except Exception as e:
            print(f"[SYSTEM ERROR] Unexpected Bridge Exception: {e}")
            
        print("[SYSTEM] Awaiting next environmental state...")
        cycle += 1
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_inference_loop())
