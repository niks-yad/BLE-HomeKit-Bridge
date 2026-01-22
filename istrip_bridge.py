#!/usr/bin/env python3
"""
iStrip+ BLE to HTTP Bridge for Homebridge (Optimized)
Provides HTTP API for controlling iStrip+ LED strips via Bluetooth LE
Features: Persistent connection, Command queue, File logging
"""

from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from bleak import BleakClient, BleakScanner
import asyncio
import logging
import sys
import os
import threading
import time
import colorsys

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'bridge.log')

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# iStrip+ Configuration
CHAR_UUID = "0000ac52-1212-efde-1523-785fedbeda25"
DEVICE_MAC = "DD:DA:EC:63:26:E0"

# State Persistence
state = {
    "r": 255,
    "g": 255,
    "b": 255,
    "brightness": 100,
    "power": True
}

class PayloadGenerator:
    """Generates AES-encrypted payloads for iStrip+ LED commands"""
    KEY = bytes([
        0x34, 0x52, 0x2A, 0x5B,
        0x7A, 0x6E, 0x49, 0x2C,
        0x08, 0x09, 0x0A, 0x9D,
        0x8D, 0x2A, 0x23, 0xF8
    ])
    
    HEADER = bytes([0x54, 0x52, 0x00, 0x57]) # TR header
    GROUP_ID = 1
    
    def __init__(self):
        self._cipher = AES.new(self.KEY, AES.MODE_ECB)
    
    def get_rgb_payload(self, red, green, blue, brightness=100, speed=100):
        """Generate RGB payload"""
        payload = bytearray(16)
        payload[0:4] = self.HEADER
        payload[4] = 2  # CommandType.Rgb
        payload[5] = self.GROUP_ID
        payload[6] = 0x00
        payload[7] = red
        payload[8] = green
        payload[9] = blue
        payload[10] = brightness
        payload[11] = speed
        return self._encrypt(payload)
    
    def get_off_payload(self, brightness=0, speed=100):
        """Generate OFF payload"""
        payload = bytearray(16)
        payload[0:4] = self.HEADER
        payload[4] = 2  # CommandType.Rgb
        payload[5] = self.GROUP_ID
        payload[6:9] = b'\x00\x00\x00'
        payload[9] = 0x00
        payload[10] = brightness
        payload[11] = speed
        return self._encrypt(payload)
    
    def _encrypt(self, payload: bytearray) -> bytes:
        """Encrypt payload"""
        assert len(payload) == 16
        return self._cipher.encrypt(bytes(payload))

pg = PayloadGenerator()

class BLEWorker:
    def __init__(self):
        self.queue = None
        self.client = None
        self.loop = None
        self._stop_event = threading.Event()
        self.current_mac = None

    async def run(self):
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue()
        logger.info("BLE Worker started.")
        
        while not self._stop_event.is_set():
            if not DEVICE_MAC:
                await asyncio.sleep(1)
                continue

            try:
                # Handle MAC change
                if self.current_mac != DEVICE_MAC:
                    if self.client:
                        logger.info(f"MAC changed, disconnecting from {self.current_mac}")
                        await self.client.disconnect()
                        self.client = None
                    self.current_mac = DEVICE_MAC

                # Connection Management
                if not self.client or not self.client.is_connected:
                    logger.info(f"Attempting connection to {DEVICE_MAC}...")
                    self.client = BleakClient(DEVICE_MAC, timeout=10.0)
                    await self.client.connect()
                    logger.info(f"Connected to {DEVICE_MAC}")

                # Process queue
                try:
                    payload = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    start_time = time.time()
                    await self.client.write_gatt_char(CHAR_UUID, payload, response=False)
                    logger.info(f"Command sent in {time.time() - start_time:.3f}s")
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    continue

            except Exception as e:
                logger.error(f"BLE Worker Error: {e}")
                if self.client:
                    try:
                        await self.client.disconnect()
                    except:
                        pass
                self.client = None
                await asyncio.sleep(2) # Backoff before retry

    def add_command(self, payload):
        if self.loop and self.queue:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, payload)
            logger.info("Command added to queue")
        else:
            logger.warning("Worker not ready, command dropped")

ble_worker = BLEWorker()

def start_worker():
    def _run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ble_worker.run())
    
    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()

@app.route('/status', methods=['GET'])
def status():
    """Health check and state endpoint"""
    return jsonify({
        "status": "ok",
        "power": state["power"],
        "r": state["r"],
        "g": state["g"],
        "b": state["b"],
        "brightness": state["brightness"],
        "device_mac": DEVICE_MAC,
        "is_connected": ble_worker.client.is_connected if ble_worker.client else False
    })

@app.route('/hex_status', methods=['GET'])
def hex_status():
    """Return current color as hex string for Homebridge plugin"""
    if not state["power"]:
        return "000000"
    hex_str = f"{state['r']:02x}{state['g']:02x}{state['b']:02x}"
    return hex_str

@app.route('/on', methods=['GET', 'POST'])
def turn_on():
    """Turn LED on with optional RGB color, HSL color, HEX color, and brightness"""
    global state
    try:
        r = request.args.get('r')
        g = request.args.get('g')
        b = request.args.get('b')
        hue = request.args.get('hue')
        sat = request.args.get('sat')
        hex_val = request.args.get('hex')
        brightness = request.args.get('brightness')
        
        state["power"] = True
        
        if brightness is not None:
            state["brightness"] = max(0, min(100, int(brightness)))
        
        if hex_val:
            hex_val = hex_val.lstrip('#')
            state["r"] = int(hex_val[0:2], 16)
            state["g"] = int(hex_val[2:4], 16)
            state["b"] = int(hex_val[4:6], 16)
        elif r is not None and g is not None and b is not None:
            state["r"] = int(r)
            state["g"] = int(g)
            state["b"] = int(b)
        elif hue is not None and sat is not None:
            h = float(hue) / 360.0
            s = float(sat) / 100.0
            v = state["brightness"] / 100.0
            rgb = colorsys.hsv_to_rgb(h, s, v)
            state["r"] = int(rgb[0]*255)
            state["g"] = int(rgb[1]*255)
            state["b"] = int(rgb[2]*255)
        
        state["r"] = max(0, min(255, state["r"]))
        state["g"] = max(0, min(255, state["g"]))
        state["b"] = max(0, min(255, state["b"]))
        
        payload = pg.get_rgb_payload(state["r"], state["g"], state["b"], state["brightness"])
        ble_worker.add_command(payload)
        
        return jsonify({
            "status": "success", 
            "r": state["r"], "g": state["g"], "b": state["b"], 
            "brightness": state["brightness"]
        })
    except Exception as e:
        logger.error(f"Error in turn_on: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/off', methods=['GET', 'POST'])
def turn_off():
    """Turn LED off"""
    global state
    try:
        state["power"] = False
        payload = pg.get_off_payload()
        ble_worker.add_command(payload)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in turn_off: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/discover', methods=['GET'])
def discover():
    """Discover nearby iStrip+ devices"""
    async def scan():
        devices = await BleakScanner.discover(timeout=5.0)
        istrip_devices = []
        for d in devices:
            name = d.name or ""
            if any(x in name for x in ["SSL-", "YH-", "iStrip"]):
                istrip_devices.append({"name": name, "address": d.address, "rssi": d.rssi})
        return istrip_devices
    
    try:
        loop = asyncio.new_event_loop()
        devices = loop.run_until_complete(scan())
        return jsonify({"devices": devices})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/set_device', methods=['POST'])
def set_device():
    global DEVICE_MAC
    mac = request.json.get('mac')
    if mac:
        DEVICE_MAC = mac.upper()
        return jsonify({"status": "success", "mac": DEVICE_MAC})
    return jsonify({"status": "error", "message": "MAC address required"}), 400

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='iStrip+ BLE HTTP Bridge')
    parser.add_argument('--mac', help='BLE device MAC address')
    parser.add_argument('--port', type=int, default=5000, help='HTTP server port')
    parser.add_argument('--host', default='0.0.0.0', help='HTTP server host')
    args = parser.parse_args()
    
    if args.mac:
        DEVICE_MAC = args.mac.upper()
    
    start_worker()
    logger.info(f"Starting optimized bridge on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
