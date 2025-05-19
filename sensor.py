"""Sensor for BeReal Time integration."""

from __future__ import annotations

import json
import datetime
from datetime import timedelta

import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_time_interval


SCAN_INTERVAL = timedelta(seconds=5)
BEREAL_API = "https://mobile-l7.bereal.com/api/bereal/moments/last/us-central"


async def async_setup_platform(
    hass: HomeAssistant,
    _config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the BeReal Time sensor platform."""
    if discovery_info is None:
        return
    sensor = BeRealSensor(hass)
    async_add_entities([sensor])
    async_track_time_interval(hass, sensor.async_update, SCAN_INTERVAL)


class BeRealSensor(SensorEntity):
    """Sensor for BeReal Time."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the BeReal Time sensor."""
        self.hass = hass
        self._attr_name = "BeReal Time"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self, _now=None) -> None:
        """Fetch new state data for the sensor."""
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(BEREAL_API, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()

                parsed = self._parse_bereal_data(data)

                self._attr_native_value = parsed.get("instance", None)
                self._attr_extra_state_attributes = {
                    "api_parsed": parsed,
                    "api_raw": json.dumps(data),
                    "current_time_utc": parsed.get("current_time_utc"),
                }

        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            self._attr_native_value = "error"
            self._attr_extra_state_attributes = {
                "api_raw": f"Error: {err}",
                "api_parsed": {},
                "current_time_utc": None,
            }

    def _parse_bereal_data(self, data: dict) -> dict:
        """Parse and enrich BeReal API response with UTC Unix timestamps (ms)."""
        result = data.copy()

        try:
            if "startDate" in result:
                result["startDate"] = int(
                    datetime.datetime.fromisoformat(
                        result["startDate"].replace("Z", "+00:00")
                    ).timestamp()
                    * 1000
                )
            if "endDate" in result:
                result["endDate"] = int(
                    datetime.datetime.fromisoformat(
                        result["endDate"].replace("Z", "+00:00")
                    ).timestamp()
                    * 1000
                )
            if "localDate" in result and "localTime" in result:
                local_str = f"{result['localDate']}T{result['localTime']}:00"
                local_dt = datetime.datetime.fromisoformat(local_str)
                result["localDateTime"] = int(local_dt.timestamp() * 1000)
        except (ValueError, KeyError) as e:
            result["error"] = f"Date parse error: {e}"
            return result

        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)
        current_utc = int(now_utc.timestamp() * 1000)
        result["current_time_utc"] = current_utc

        # Determine instance
        start = result.get("startDate")
        end = result.get("endDate")
        local_timestamp = result.get("localDateTime")
        instance = None

        if start is not None and end is not None and local_timestamp is not None:
            now_local = datetime.datetime.now().astimezone()  # Local timezone
            current_local_date = now_local.date()

            bereal_local_date = (
                datetime.datetime.fromtimestamp(local_timestamp / 1000)
                .astimezone()
                .date()
            )

            if current_local_date > bereal_local_date:
                instance = "waiting"
            elif start <= current_utc <= end:
                instance = "now"
            elif current_utc < start:
                instance = "waiting"
            elif current_utc > end:
                instance = "past"

        result["instance"] = instance
        return result
