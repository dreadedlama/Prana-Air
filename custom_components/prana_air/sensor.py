from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PranaAirCoordinator


SENSORS = {
    1: {"name": "AQI", "key": "aqi", "device_class": SensorDeviceClass.AQI, "unit": None},
    3: {"name": "PM2.5", "key": "pm25", "device_class": SensorDeviceClass.PM25, "unit": "µg/m³"},
    4: {"name": "PM10", "key": "pm10", "device_class": SensorDeviceClass.PM10, "unit": "µg/m³"},
    5: {"name": "PM1", "key": "pm1", "device_class": SensorDeviceClass.PM1, "unit": "µg/m³"},
    11: {"name": "Temperature", "key": "temperature", "device_class": SensorDeviceClass.TEMPERATURE, "unit": "°C"},
    30: {"name": "Temperature Fahrenheit", "key": "temperature_f", "device_class": None, "unit": "°F"},
    12: {"name": "Humidity", "key": "humidity", "device_class": SensorDeviceClass.HUMIDITY, "unit": "%"},
    18: {"name": "TVOC", "key": "tvoc", "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS, "unit": "ppm"},
    71: {"name": "Particle Count 0.3µm", "key": "particle_count_0p3", "device_class": None, "unit": None},
    72: {"name": "Particle Count 0.5µm", "key": "particle_count_0p5", "device_class": None, "unit": None},
    73: {"name": "Particle Count 1.0µm", "key": "particle_count_1p0", "device_class": None, "unit": None},
    74: {"name": "Particle Count 3.0µm", "key": "particle_count_3p0", "device_class": None, "unit": None},
    75: {"name": "Particle Count 5.0µm", "key": "particle_count_5p0", "device_class": None, "unit": None},
    76: {"name": "Particle Count 10.0µm", "key": "particle_count_10p0", "device_class": None, "unit": None},
    13: {"name": "Noise", "key": "noise", "device_class": SensorDeviceClass.SOUND_PRESSURE, "unit": "dB"},
}


# US EPA AQI breakpoints. PM2.5 uses the current 2024 EPA breakpoints.
# PM2.5 is truncated to 0.1 µg/m³ and PM10 is truncated to an integer
# before calculating the AQI. The final US AQI is the highest AQI produced
# by PM2.5 or PM10.
PM25_BREAKPOINTS = (
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
)

PM10_BREAKPOINTS = (
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 500),
)


def _truncate_pm25(value: float) -> float:
    return int(value * 10) / 10


def _truncate_pm10(value: float) -> int:
    return int(value)


def _aqi_from_breakpoints(value, breakpoints):
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= value <= c_high:
            return round(
                ((i_high - i_low) / (c_high - c_low))
                * (value - c_low)
                + i_low
            )
    return None


def calculate_us_aqi(measurements: dict) -> int | None:
    """Calculate US AQI from PM2.5 and PM10, using the highest sub-index."""
    candidates = []

    pm25 = measurements.get(3)
    if pm25 is not None:
        try:
            pm25 = _truncate_pm25(float(pm25))
            aqi = _aqi_from_breakpoints(pm25, PM25_BREAKPOINTS)
            if aqi is not None:
                candidates.append(aqi)
        except (TypeError, ValueError):
            pass

    pm10 = measurements.get(4)
    if pm10 is not None:
        try:
            pm10 = _truncate_pm10(float(pm10))
            aqi = _aqi_from_breakpoints(pm10, PM10_BREAKPOINTS)
            if aqi is not None:
                candidates.append(aqi)
        except (TypeError, ValueError):
            pass

    return max(candidates) if candidates else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PranaAirCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PranaAirSensor(coordinator, entry, sensor_id, description)
        for sensor_id, description in SENSORS.items()
    ]

    entities.extend(
        [
            PranaAirUsAqiSensor(coordinator, entry),
            PranaAirSerialSensor(coordinator, entry),
            PranaAirHardwareSensor(coordinator, entry),
            PranaAirLastSeenSensor(coordinator, entry),
        ]
    )

    async_add_entities(entities)


class PranaAirBaseEntity(CoordinatorEntity[PranaAirCoordinator], SensorEntity):
    def __init__(self, coordinator, entry, name, key):
        super().__init__(coordinator)
        self._attr_name = name
        # Explicit entity naming: prana_air_<key>
        self._attr_has_entity_name = False
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        serial = self.coordinator.data.get("serial_no")
        hw_id = self.coordinator.data.get("hw_id")

        return DeviceInfo(
            identifiers={(DOMAIN, "prana_air_meter")},
            name="Prana Air AQI Meter",
            manufacturer="Prana Air",
            model=f"AQI.in ESP32-C3 / HW {hw_id or 'Unknown'}",
            serial_number=serial,
        )


class PranaAirSensor(PranaAirBaseEntity):
    def __init__(self, coordinator, entry, sensor_id, description):
        super().__init__(
            coordinator,
            entry,
            description["name"],
            description["key"],
        )
        self._sensor_id = sensor_id
        self._attr_device_class = description["device_class"]
        self._attr_native_unit_of_measurement = description["unit"]

        if sensor_id != 1:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        value = self.coordinator.data.get("measurements", {}).get(self._sensor_id)
        if value is None:
            return None
        return float(value) if self._sensor_id == 30 else value

    @property
    def extra_state_attributes(self):
        return {
            "serial_number": self.coordinator.data.get("serial_no"),
            "hardware_id": self.coordinator.data.get("hw_id"),
            "sensor_id": self._sensor_id,
        }


class PranaAirUsAqiSensor(PranaAirBaseEntity):
    """US AQI calculated from PM2.5 and PM10."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "AQI US", "aqi_us")
        self._attr_device_class = SensorDeviceClass.AQI

    @property
    def native_value(self):
        return calculate_us_aqi(
            self.coordinator.data.get("measurements", {})
        )

    @property
    def extra_state_attributes(self):
        measurements = self.coordinator.data.get("measurements", {})
        return {
            "calculation": "US EPA AQI",
            "pm2_5": measurements.get(3),
            "pm10": measurements.get(4),
        }


class PranaAirSerialSensor(PranaAirBaseEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Serial Number", "serial_number")

    @property
    def native_value(self):
        return self.coordinator.data.get("serial_no")


class PranaAirHardwareSensor(PranaAirBaseEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Hardware ID", "hardware_id")

    @property
    def native_value(self):
        return self.coordinator.data.get("hw_id")


class PranaAirLastSeenSensor(PranaAirBaseEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Last Seen", "last_seen")

    @property
    def device_class(self):
        return SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        return self.coordinator.data.get("last_seen")

    @property
    def native_unit_of_measurement(self):
        return None
