# iStrip+ BLE HomeKit Bridge 🌈

**Control your iStrip+ / Sperll / BLEDOM LED strips instantly via Apple HomeKit.**

This project solves the "slow connection" and "unstable plugin" issues common with BLE LED strips on Linux. It provides a high-performance Python bridge with a persistent BLE connection and a simple HTTP API for Homebridge integration.

---

## ⚡ Key Features

- **Instant Response**: Persistent BLE connection eliminates the 5-10s "connecting" delay.
- **Zero-Config Homebridge**: Uses a simple HTTP plugin; no complex BLE setup in Node.js.
- **Robustness**: Automatic reconnection and command queueing.
- **Enthusiast Friendly**: Built-in discovery tools and clear protocol documentation.
- **AI-Ready**: Designed to be easily customized by AI coding agents (Claude Code, Antigravity, etc.).

---

## 🛠️ Requirements

- **Hardware**: 
  - A Linux machine (Raspberry Pi, Ubuntu Home Server, etc.) with a Bluetooth adapter.
  - iStrip+ / Sperll compatible LED strip (tested on model `YH-6326E0`).
- **Software**: 
  - Python 3.9+
  - Homebridge

---

## 🚀 Quick Start

### 1. Installation
Clone this repo and install dependencies:
```bash
git clone https://github.com/niks-yad/BLE-HomeKit-Bridge.git
cd BLE-HomeKit-Bridge
python3 -m venv venv
source venv/bin/activate
pip install flask bleak pycryptodome colorsys
```

### 2. Connect your Device
Find your LED strip's MAC address:
```bash
python3 discovery.py
```
*Note: Make sure your phone's iStrip+ app is closed! BLE only allows one connection at a time.*

### 3. Run the Bridge
```bash
# Test manually first
python3 istrip_bridge.py --mac YOUR:MAC:ADDR:HERE
```

### 4. Homebridge Setup
Install `homebridge-http-rgb-bulb` and add this to your `config.json`:
```json
{
    "accessory": "HttpRGB",
    "name": "LED Strip",
    "set_url": "http://localhost:5000/on?hex=%s",
    "get_url": "http://localhost:5000/hex_status"
}
```

---

## 🤖 AI-Assisted Customization (The Future)

If you have a different BLE device, you can use an **AI Coding Agent** (like Claude Code or Antigravity) to adapt this project in seconds.

### Steps to Customize using AI:
1. **Discovery**: Run `python3 discovery.py` and pipe the output to your AI agent.
2. **Analysis**: Ask the agent: *"Analyze the services and characteristics of my BLE device from this log. Which one likely handles color control?"*
3. **Adaptation**: Ask the agent: *"Modify istrip_bridge.py to use my device's Characteristic UUID and adapt the PayloadGenerator if the protocol is different."*
4. **Testing**: Tell the agent: *"Write a test script to send a 'Turn On' command to my device using the discovered protocol."*

This bridge provides the **Connection Manager** and **API Layer**—an AI can easily swap out the **Protocol Layer**.

---

## 📝 Protocol Documentation (Model YH-6326E0)

For those who like to tinker under the hood:
- **Encryption**: AES-128 ECB
- **Key**: `0x34, 0x52, 0x2A, 0x5B, 0x7A, 0x6E, 0x49, 0x2C, 0x08, 0x09, 0x0A, 0x9D, 0x8D, 0x2A, 0x23, 0xF8`
- **Write Target**: Characteristic `0000ac52-1212-efde-1523-785fedbeda25`

---

## 🆘 Troubleshooting & Tips

- **It's slow!**: Ensure the bridge is running. A persistent connection is the secret to the <100ms response time.
- **Connection Failed**: Ensure no other device (like your phone) is connected to the LED strip.
- **Logs**: Check `logs/bridge.log` for real-time debugging information.

---

## 🤝 Contributing

Enthusiasts are welcome! If you adapt this for another device brand, please submit a PR with your `PayloadGenerator` implementation.

## 📄 License
MIT
