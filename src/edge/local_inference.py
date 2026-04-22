import os
import asyncio
import datetime
import signal
import time
import httpx
import numpy as np
import onnxruntime as ort
from typing import Dict, Tuple
from dotenv import load_dotenv
from bacpypes3.apdu import AbortPDU
from database import TelemetryDB
from bacnet_translator import BACnetBridge

# Load .env BEFORE any os.environ.get() calls below.
# On the Pi this reads ~/EcoRetrofit-AI/src/edge/.env with the hotspot IPs.
# Inside Docker, the file won't exist (.dockerignore) and this is a no-op.
_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env_path):
    load_dotenv(dotenv_path=_env_path, override=False)

# ---------------------------------------------------------------------------
# Action mapping: exact values from Sinergym DEFAULT_5ZONE_DISCRETE_FUNCTION
# (sinergym/utils/constants.py). The model was trained against these numbers.
# ---------------------------------------------------------------------------
ACTION_MAP: Dict[int, Tuple[float, float]] = {
    0: (12.0, 30.0),
    1: (13.0, 29.0),
    2: (14.0, 28.0),
    3: (15.0, 27.0),
    4: (16.0, 26.0),
    5: (17.0, 25.0),
    6: (18.0, 24.0),
    7: (19.0, 23.25),
    8: (20.0, 23.25),
    9: (21.0, 23.25),
}

# ---------------------------------------------------------------------------
# VecNormalize statistics -- extracted from vec_normalize_discrete.pkl
# Observation space order (Eplus-5zone-cool-discrete-v1):
#   [0]  Month                                  <- datetime injected
#   [1]  Day of Month                           <- datetime injected
#   [2]  Hour                                   <- datetime injected
#   [3]  Site Outdoor Air Drybulb Temperature   <- outdoor_temp injected
#   [4]  Site Outdoor Air Relative Humidity
#   [5]  Site Wind Speed
#   [6]  Site Wind Direction
#   [7]  Site Diffuse Solar Radiation
#   [8]  Site Direct Solar Radiation
#   [9]  Zone Thermostat Heating Setpoint (current)
#   [10] Zone Thermostat Cooling Setpoint (current)
#   [11] Zone Air Temperature                   <- indoor_temp injected
#   [12] Zone Air Relative Humidity
#   [13] Zone Thermal Comfort Fanger PMV
#   [14] Zone People Occupant Count (near-zero variance)
#   [15] Facility Total HVAC Electric Demand Power
#   [16] Electricity:Facility (cumulative)
# ---------------------------------------------------------------------------
OBS_MEAN: np.ndarray = np.array(
    [6.51779457e+00, 1.57188284e+01, 1.14999977e+01, 9.26117130e+00,
     8.10594384e+01, 2.27252186e+00, 1.80487175e+02, 7.03206009e+01,
     1.32429443e+02, 1.82606348e+01, 2.54974688e+01, 2.18726515e+01,
     4.38057677e+01, 5.78010352e+00, 0.00000000e+00, 1.61177391e+03,
     1.52059133e+06],
    dtype=np.float32,
)

OBS_VAR: np.ndarray = np.array(
    [1.18728395e+01, 7.73648895e+01, 4.79166835e+01, 2.80709073e+01,
     2.09850861e+02, 2.96446653e+00, 1.50074504e+04, 9.15017905e+03,
     5.38903748e+04, 1.04524433e+01, 6.70095242e+00, 2.51297064e+00,
     5.53836967e+01, 7.03939119e+01, 1.99951332e-11, 6.85269219e+06,
     6.15882282e+12],
    dtype=np.float32,
)

BACKEND_URL: str = os.environ.get(
    'BACKEND_API_URL', 'http://127.0.0.1:8010/api/environment'
)
OVERRIDE_URL: str = BACKEND_URL.replace('/api/environment', '/api/override')

# Graceful shutdown flag
_shutdown: bool = False


def _handle_signal(sig: int, frame: object) -> None:
    global _shutdown
    print(f"\n[SYSTEM] Signal {sig} received -- shutting down after current cycle...")
    _shutdown = True


def build_observation(indoor_temp: float, outdoor_temp: float) -> np.ndarray:
    """Construct and normalize a 17-dim observation vector matching
    the Sinergym Eplus-5zone-cool-discrete-v1 observation space."""
    now: datetime.datetime = datetime.datetime.now()
    raw: np.ndarray = np.copy(OBS_MEAN)
    raw[0] = float(now.month)
    raw[1] = float(now.day)
    raw[2] = float(now.hour)
    raw[3] = outdoor_temp
    raw[11] = indoor_temp
    norm: np.ndarray = (raw - OBS_MEAN) / np.sqrt(OBS_VAR + 1e-8)
    norm = np.clip(norm, -10.0, 10.0)
    return np.array([norm], dtype=np.float32)


async def run_inference_loop(db: TelemetryDB) -> None:
    bridge: BACnetBridge = BACnetBridge()
    bacnet_device: str = os.environ.get("BACNET_DEVICE_ADDR", "192.168.5.24")
    object_identifier: str = os.environ.get("BACNET_OBJECT_ID", "analogValue:1")

    # Pre-initialize BACnet application binding before entering the loop
    # to avoid a ~200ms penalty on the first write cycle.
    try:
        await bridge.initialize()
    except Exception as e:
        print(f"[SYSTEM WARNING] BACnet pre-init failed (will retry on first write): {e}")

    print("[AI] Loading ONNX Inference Session...")
    ort_session: ort.InferenceSession = ort.InferenceSession('models/ecoretrofit_3M.onnx')
    print("[AI] ONNX session ready. Entering inference loop.")

    cycle: int = 1
    async with httpx.AsyncClient(timeout=2.0) as http:
        while not _shutdown:
            print(f"\n--- Inference Cycle {cycle} ---")

            # 1. Parallel fetch: environment + override status in one RTT
            indoor_temp: float = 21.5
            outdoor_temp: float = 15.0
            override_active: bool = False

            try:
                env_task = http.get(BACKEND_URL)
                ov_task = http.get(OVERRIDE_URL)
                results = await asyncio.gather(env_task, ov_task, return_exceptions=True)

                # Parse environment response
                if isinstance(results[0], httpx.Response) and results[0].is_success:
                    env_data: Dict[str, float] = results[0].json()
                    indoor_temp = float(env_data.get("indoor_temp", 21.5))
                    outdoor_temp = float(env_data.get("outdoor_temp", 15.0))
                elif isinstance(results[0], Exception):
                    print(f"[WARNING] Backend env unreachable: {results[0]}")

                # Parse override response
                if isinstance(results[1], httpx.Response) and results[1].is_success:
                    override_active = results[1].json().get("override_active", False)
                elif isinstance(results[1], Exception):
                    pass  # Fail open: allow BACnet writes if override check fails

            except Exception as e:
                print(f"[WARNING] Backend unreachable, using fallback values: {e}")

            # 2. Build normalized observation vector
            obs_array: np.ndarray = build_observation(indoor_temp, outdoor_temp)

            # 3. Run ONNX inference (timed for latency reporting)
            t0: float = time.perf_counter()
            onnx_outputs = ort_session.run(None, {'observation': obs_array})
            latency_ms: float = (time.perf_counter() - t0) * 1000.0

            action: int = int(onnx_outputs[0][0])
            heating_setpoint, cooling_setpoint = ACTION_MAP.get(action, (18.0, 24.0))

            print(
                f"[AI] Action {action} -> "
                f"Heating: {heating_setpoint}C | Cooling: {cooling_setpoint}C "
                f"(Indoor: {indoor_temp}C | Outdoor: {outdoor_temp}C) "
                f"[{latency_ms:.2f}ms]"
            )

            # 4. Log telemetry to InfluxDB (includes inference latency)
            db.log_step(
                indoor_temp=indoor_temp,
                heating_setpoint=heating_setpoint,
                cooling_setpoint=cooling_setpoint,
                latency_ms=latency_ms,
            )

            # 5. Broadcast setpoints to BACnet (skipped if override active)
            if override_active:
                print("[SYSTEM] Manual override active -- skipping BACnet write.")
            else:
                try:
                    print("[BACNET] Bridging parameters to physical hardware...")
                    await bridge.write_setpoint(
                        device_address=bacnet_device,
                        object_identifier=object_identifier,
                        value=heating_setpoint,
                    )
                except AbortPDU as e:
                    print(f"[NETWORK WARNING] BACnet Abort Exception Caught: {e}")
                except Exception as e:
                    print(f"[SYSTEM ERROR] Unexpected Bridge Exception: {e}")

            print("[SYSTEM] Awaiting next environmental state...")
            cycle += 1
            await asyncio.sleep(2)

    print("[SYSTEM] Inference loop exited cleanly.")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    print("[SYSTEM] Booting Edge Control Inference Sequence...")
    db = TelemetryDB()
    try:
        asyncio.run(run_inference_loop(db))
    finally:
        print("[SYSTEM] Closing InfluxDB connection...")
        db.close()
        print("[SYSTEM] Shutdown complete.")