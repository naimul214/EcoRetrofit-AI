import asyncio
from bacpypes3.ipv4.app import NormalApplication, IPv4Address, DeviceObject
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import Real
from bacpypes3.basetypes import ObjectIdentifier


class BACnetBridge:
    def __init__(self, local_address: str = "0.0.0.0") -> None:
        self.local_address = local_address
        self.app = None

    async def initialize(self) -> None:
        """Pre-initialize the BACnet application binding.
        Call this once before the inference loop to avoid a ~200ms
        startup penalty on the first write_setpoint() call."""
        if not self.app:
            print("[SYSTEM] Initializing BACnet IPv4 Application Binding...")
            device_info = DeviceObject(
                objectIdentifier=("device", 100),
                objectName="EcoRetrofit Edge Bridge",
                vendorIdentifier=15,
            )
            self.app = NormalApplication(device_info, IPv4Address(self.local_address))
            print("[SYSTEM] BACnet application ready.")

    async def write_setpoint(
        self,
        device_address: str,
        object_identifier: str,
        value: float,
    ) -> None:
        """
        Send a BACnet WritePropertyRequest to update an Analog Value object.
        Exceptions are NOT caught here -- they propagate to the caller so the
        inference loop can handle them with its own retry/logging strategy.
        """
        if not self.app:
            await self.initialize()

        print(f"[BACNET] Targeting Device: {device_address} | Object: {object_identifier}")
        print(f"[BACNET] Transmitting Write Request: {value}")

        obj_id = ObjectIdentifier(object_identifier)
        await self.app.write_property(
            Address(device_address),
            obj_id,
            "presentValue",
            Real(value),
        )
        print("[BACNET] Write Request Successful.")


async def main() -> None:
    print("[SYSTEM] Booting Asynchronous BACnet Bridge...")
    bridge = BACnetBridge()
    await bridge.initialize()
    dummy_device = "192.168.1.100"
    analog_value_obj = "analogValue:1"
    new_setpoint = 22.5
    print("[SYSTEM] Executing Mock Translation Layer Test...")
    await bridge.write_setpoint(dummy_device, analog_value_obj, new_setpoint)
    print("[SYSTEM] BACnet Translation Test Concluded.")


if __name__ == "__main__":
    asyncio.run(main())
