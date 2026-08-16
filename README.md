# Prana Air / AQI.IN Home Assistant Integration

A custom Home Assistant integration for **Prana Air air-quality monitors**.

This integration receives the data sent by the Prana Air device to AQI.IN and exposes the measurements as Home Assistant entities.

> **Note:** This is an unofficial custom integration and is not affiliated with or endorsed by Prana Air or AQI.IN.

> **Read the Write-up:** For a detailed, story-driven breakdown of how I reversed engineered this device and intercepted its requests, check out the blog post: [Taking Control of the Prana Air AQI Meter](https://dreadedlama.com/articles/prana-air.html).

## Features

- Receive Prana Air sensor data in Home Assistant
- AQI
- PM1
- PM2.5
- PM10
- Temperature
- Temperature Fahrenheit
- Humidity
- TVOC
- Particle counts
- Noise level
- Device serial number
- Hardware ID
- Last Seen timestamp
- All sensors grouped under a single Home Assistant device
- Optional forwarding of data back to AQI.IN
- Configure cloud forwarding through Home Assistant automations
- Use the sensor data in dashboards, automations, scripts, and templates

## How It Works

The Prana Air device normally sends data to:

```text
[http://data.aqi.in/api/v1/SendSensordata](http://data.aqi.in/api/v1/SendSensordata)
