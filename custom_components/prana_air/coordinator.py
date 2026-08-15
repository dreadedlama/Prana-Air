from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger("prana_air")


class PranaAirCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Store pushed Prana Air data."""

    def __init__(self, hass) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Prana Air",
            update_interval=None,
        )
        self.data = {
            "serial_no": None,
            "hw_id": None,
            "measurements": {},
            "last_seen": None,
        }

    def process_data(self, payload: dict[str, Any]) -> None:
        measurements = {}

        for item in payload.get("data", []):
            if not isinstance(item, list) or len(item) != 2:
                continue
            try:
                sensor_id = int(item[0])
            except (TypeError, ValueError):
                continue
            measurements[sensor_id] = item[1]

        self.data = {
            "serial_no": payload.get("serialNo"),
            "hw_id": payload.get("hwId"),
            "measurements": measurements,
            "last_seen": dt_util.now(),
        }

        self.async_set_updated_data(self.data)
