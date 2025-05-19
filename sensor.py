"""Sensor for BeReal Time integration."""

from __future__ import annotations

import json
import datetime
from datetime import timedelta

import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

DOMAIN = "bereal_time"
DEFAULT_REGION = "us-central"

SHORT_INTERVAL = timedelta(seconds=5)
LONG_INTERVAL = timedelta(hours=2)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BeReal Time sensor from a config entry."""
    region = entry.data.get("region", DEFAULT_REGION)
    sensor = BeRealSensor(hass, region)
    async_add_entities([sensor], True)


class BeRealSensor(SensorEntity):
    """Sensor for BeReal Time."""

    def __init__(self, hass: HomeAssistant, region: str) -> None:
        self.hass = hass
        self._region = region
        self._api_url = f"https://mobile-l7.bereal.com/api/bereal/moments/last/{region}"
        self._attr_name = f"BeReal Time ({region})"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        self._attr_unique_id = f"bereal_time_{region}"
        self._unsub_timer = None
        self._current_interval = SHORT_INTERVAL

    async def async_added_to_hass(self) -> None:
        """Called when entity is added to Home Assistant."""
        await self._schedule_next_update(self._current_interval)

    async def async_will_remove_from_hass(self) -> None:
        """Cleanup when entity is removed."""
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    async def _schedule_next_update(self, interval: timedelta) -> None:
        """Schedule the next update after given interval."""
        if self._unsub_timer:
            self._unsub_timer()

        self._current_interval = interval

        @callback
        def _run(_now):
            self.hass.async_create_task(self.async_update())

        self._unsub_timer = async_call_later(self.hass, interval.total_seconds(), _run)

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(self._api_url, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()

                parsed = self._parse_bereal_data(data)
                instance = parsed.get("instance")

                # Decide polling interval
                if instance == "now":
                    next_interval = SHORT_INTERVAL
                elif instance == "waiting":
                    next_interval = SHORT_INTERVAL
                elif instance == "past":
                    next_interval = LONG_INTERVAL
                else:
                    next_interval = SHORT_INTERVAL  # fallback

                self._attr_native_value = instance
                self._attr_extra_state_attributes = {
                    "api_parsed": parsed,
                    "api_raw": json.dumps(data),
                    "current_time_utc": parsed.get("current_time_utc"),
                    "current_scan_interval": int(next_interval.total_seconds()),
                }

        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            next_interval = SHORT_INTERVAL
            self._attr_native_value = "error"
            self._attr_extra_state_attributes = {
                "api_raw": f"Error: {err}",
                "api_parsed": {},
                "current_time_utc": None,
                "current_scan_interval": int(next_interval.total_seconds()),
            }

        await self._schedule_next_update(next_interval)

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

        start = result.get("startDate")
        end = result.get("endDate")
        local_timestamp = result.get("localDateTime")
        instance = None

        if start is not None and end is not None and local_timestamp is not None:
            now_local = datetime.datetime.now().astimezone()
            current_local_date = now_local.date()
            bereal_local_date = (
                datetime.datetime.fromtimestamp(local_timestamp / 1000)
                .astimezone()
                .date()
            )

            six_am = now_local.replace(hour=6, minute=0, second=0, microsecond=0)

            if current_local_date > bereal_local_date:
                instance = "waiting"
            elif start <= current_utc <= end:
                instance = "now"
            elif current_utc < start:
                instance = "waiting"
            elif current_utc > end:
                instance = "past"

            # Force to "waiting" after 6AM if today's post is missing
            if now_local >= six_am and current_local_date > bereal_local_date:
                instance = "waiting"

        result["instance"] = instance
        return result
