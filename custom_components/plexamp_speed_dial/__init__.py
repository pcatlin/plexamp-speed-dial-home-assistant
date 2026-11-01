"""Plexamp Speed Dial Home Assistant integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import SpeedDialApiClient, SpeedDialApiError
from .const import (
    ATTR_FAVORITE_ID,
    ATTR_LABEL,
    CONF_BASE_URL,
    DOMAIN,
    SERVICE_PLAY,
)
from .coordinator import SpeedDialCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON]

PLAY_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(ATTR_FAVORITE_ID, "target"): cv.positive_int,
        vol.Exclusive(ATTR_LABEL, "target"): cv.string,
    },
    required=True,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML is not supported; config entries only."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    base_url = entry.data[CONF_BASE_URL]
    session = async_get_clientsession(hass)
    client = SpeedDialApiClient(session, base_url)
    coordinator = SpeedDialCoordinator(hass, client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(str(err)) from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_handle_play(call: ServiceCall) -> None:
        data: dict[str, Any] = dict(call.data)
        favorite_id = data.get(ATTR_FAVORITE_ID)
        label = data.get(ATTR_LABEL)

        entries = list(hass.data.get(DOMAIN, {}).values())
        if not entries:
            raise HomeAssistantError("Plexamp Speed Dial is not configured")

        client: SpeedDialApiClient | None = None
        target_id: int | None = None

        if favorite_id is not None:
            target_id = int(favorite_id)
            client = entries[0]["client"]
        elif label:
            for stored in entries:
                coord: SpeedDialCoordinator = stored["coordinator"]
                match = coord.favorite_by_label(str(label))
                if match is not None:
                    target_id = int(match["id"])
                    client = stored["client"]
                    break
            if target_id is None or client is None:
                raise HomeAssistantError(f"No speed dial found with label {label!r}")
        else:
            raise HomeAssistantError("Provide favorite_id or label")

        try:
            await client.async_play_favorite(target_id)
        except SpeedDialApiError as err:
            raise HomeAssistantError(str(err)) from err

    if not hass.services.has_service(DOMAIN, SERVICE_PLAY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PLAY,
            async_handle_play,
            schema=PLAY_SERVICE_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_PLAY)
    return unload_ok
