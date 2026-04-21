import asyncio
from bacpypes3.ipv4.app import NormalApplication, IPv4Address, DeviceObject
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import Real
from bacpypes3.basetypes import ObjectIdentifier

class BACnetBridge:
    def __init__(self, local_address="0.0.0.0"):
        self.local_address = local_address
        self.app = None

    async def write_setpoint(self, device_address: str, object_identifier: str, value: float):
        """Constructs and sends a BACnet WritePropertyRequest to update an Analog Value."""
        if not self.app:
            print("[SYSTEM] Initializing BACnet IPv4 Application Binding...")
            device_info = DeviceObject(
                objectIdentifier=("device", 100),
                objectName="EcoRetrofit Edge Bridge",
                vendorIdentifier=15
            )
            self.app = NormalApplication(device_info, IPv4Address(self.local_address))
            
        print(f"[BACNET] Targeting Device: {device_address} | Object: {object_identifier}")
        print(f"[BACNET] Transmitting Write Request: {value}")
        
        try:
            # Cast explicitly correctly matching ObjectIdentifier schema safely
            obj_id = ObjectIdentifier(object_identifier)
            
            # write_property(address, obj_id, prop_id, value)
            await self.app.write_property(
                Address(device_address),
                obj_id,
                "presentValue",
                Real(value)
            )
            print("[BACNET] Write Request Successful.")
            
        except Exception as e:
            print(f"[BACNET ERROR] Write Failed: {e}")

async def main():
    print("[SYSTEM] Booting Asynchronous BACnet Bridge...")
    bridge = BACnetBridge()
    
    # Mock parameters for testing bounds efficiently
    dummy_device = "192.168.1.100"
    analog_value_obj = "analogValue:1"
    new_setpoint = 22.5
    
    print("[SYSTEM] Executing Mock Translation Layer Test...")
    await bridge.write_setpoint(dummy_device, analog_value_obj, new_setpoint)
    print("[SYSTEM] BACnet Translation Test Concluded.")

if __name__ == "__main__":
    asyncio.run(main())
