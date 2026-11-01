"""Device actions — pick a speed dial in an automation or script."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_TYPE
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .api import SpeedDialApiError
from .const import ATTR_FAVORITE_ID, DOMAIN
from .coordinator import speed_dial_display_name

_LOGGER = logging.getLogger(__name__)

ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): cv.string,
        vol.Required(ATTR_FAVORITE_ID): vol.All(vol.Coerce(int), vol.Range(min=1)),
    },
    extra=vol.ALLOW_EXTRA,
)


def _entry_id_for_device(hass: HomeAssistant, device_id: str) -> str | None:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.domain == DOMAIN:
            return entry_id
    return None


def _actions_for_favorites(device_id: str, favorites: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[tuple[int, str]] = []
    for row in favorites:
        try:
            favorite_id = int(row["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if favorite_id < 1:
            continue
        prepared.append((favorite_id, speed_dial_display_name(row)))

    counts: dict[str, int] = {}
    for _, text in prepared:
        counts[text] = counts.get(text, 0) + 1

    actions: list[dict[str, Any]] = []
    for favorite_id, text in prepared:
        shown = f"{text} ({favorite_id})" if counts[text] > 1 else text
        actions.append(
            {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: shown,
                ATTR_FAVORITE_ID: favorite_id,
            }
        )
    return actions


async def async_get_actions(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    """List one combobox row per speed dial."""
    entry_id = _entry_id_for_device(hass, device_id)
    if entry_id is None:
        return []
    stored = hass.data.get(DOMAIN, {}).get(entry_id)
    if not stored:
        return []
    return _actions_for_favorites(device_id, list(stored["coordinator"].data or []))


async def async_call_action_from_config(
    hass: HomeAssistant,
    config: ConfigType,
    variables: dict[str, Any],
    context: Context | None,
) -> None:
    """Play the favorite id stored when the speed dial was chosen."""
    del variables, context
    entry_id = _entry_id_for_device(hass, config[CONF_DEVICE_ID])
    if entry_id is None:
        raise HomeAssistantError("Plexamp Speed Dial device is no longer available")
    stored = hass.data.get(DOMAIN, {}).get(entry_id)
    if not stored:
        raise HomeAssistantError("Plexamp Speed Dial is not configured")

    favorite_id = int(config[ATTR_FAVORITE_ID])
    try:
        await stored["client"].async_play_favorite(favorite_id)
    except SpeedDialApiError as err:
        raise HomeAssistantError(str(err)) from err
    _LOGGER.debug("Played speed dial id=%s", favorite_id)
