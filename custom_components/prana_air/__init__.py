from __future__ import annotations

import json
import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import PranaAirCoordinator

_LOGGER = logging.getLogger(DOMAIN)


class PranaAirSendSensorDataView(HomeAssistantView):
    """Receive Prana Air sensor data."""

    url = "/api/v1/SendSensordata"
    name = "api:prana_air:send_sensor_data"
    requires_auth = False

    def __init__(self, coordinator: PranaAirCoordinator) -> None:
        self.coordinator = coordinator

    async def post(self, request: web.Request) -> web.Response:
        try:
            form = await request.post()
            json_data = form.get("jsonData")

            if not json_data:
                return web.Response(status=400, text="Missing jsonData")

            payload = json.loads(json_data)

            if not isinstance(payload, dict):
                return web.Response(status=400, text="Invalid jsonData")

            self.coordinator.process_data(payload)

            _LOGGER.debug(
                "Prana Air data received from %s: %s",
                payload.get("serialNo"),
                payload,
            )

            return web.Response(status=200, text="OK")

        except json.JSONDecodeError:
            _LOGGER.exception("Invalid Prana Air JSON")
            return web.Response(status=400, text="Invalid JSON")
        except Exception:
            _LOGGER.exception("Error processing Prana Air request")
            return web.Response(status=500, text="Error")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = PranaAirCoordinator(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.http.register_view(PranaAirSendSensorDataView(coordinator))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
