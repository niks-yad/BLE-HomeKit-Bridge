#!/usr/bin/env python3
import asyncio
from bleak import BleakScanner

async def main():
    print("Detailed BLE Scan (15 seconds)...")
    print("-" * 80)
    
    devices = await BleakScanner.discover(timeout=15.0, return_adv=True)
    
    print(f"\nFound {len(devices)} unique devices.\n")
    
    for address, (device, adv_data) in devices.items():
        name = device.name if device.name else "(unknown)"
        print(f"Address: {address}")
        print(f"  Name: {name}")
        print(f"  RSSI: {adv_data.rssi}")
        if adv_data.service_uuids:
            print(f"  Services: {adv_data.service_uuids}")
        if adv_data.manufacturer_data:
            print(f"  Manufacturer Data: {adv_data.manufacturer_data}")
        if adv_data.service_data:
            print(f"  Service Data: {adv_data.service_data}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
