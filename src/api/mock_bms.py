from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Commercial BMS IP Gateway")

# Simulated building state
building_state = {
    "zone_1": {
        "indoor_temp": 18.5,
        "humidity": 45.0,
        "occupancy": 1,
        "hvac_status": "OFF"
    }
}

@app.get("/api/v1/zones/1")
def get_zone_status():
    """The Raspberry Pi will call this endpoint to get the current temperature."""
    return building_state["zone_1"]

@app.post("/api/v1/zones/1/temp/{new_temp}")
def update_temp(new_temp: float):
    """You will use this to manually change the building temp during the demo."""
    building_state["zone_1"]["indoor_temp"] = new_temp
    return {"message": f"Zone 1 temp updated to {new_temp}C"}

if __name__ == "__main__":
    print("[SYSTEM] Starting Mock Commercial BMS Server on Port 8000...")
    print("[SYSTEM] Network Endpoint: http://0.0.0.0:8000/api/v1/zones/1")
    uvicorn.run(app, host="0.0.0.0", port=8000)