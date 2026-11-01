"""Config flow for Plexamp Speed Dial."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SpeedDialApiClient, SpeedDialApiError
from .const import CONF_BASE_URL, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


def _normalize_base_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    parsed = urlparse(url if "://" in url else f"http://{url}")
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Enter a full URL such as http://192.168.1.50:3322")
    return f"{parsed.scheme}://{parsed.netloc}"


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    base_url = _normalize_base_url(data[CONF_BASE_URL])
    session = async_get_clientsession(hass)
    client = SpeedDialApiClient(session, base_url)
    await client.async_test_connection()
    return {
        CONF_BASE_URL: base_url,
        CONF_NAME: data.get(CONF_NAME) or DEFAULT_NAME,
    }


class SpeedDialConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
            except ValueError:
                errors["base"] = "invalid_url"
            except SpeedDialApiError as err:
                _LOGGER.debug("Speed Dial API error: %s", err)
                if err.status in (401, 403):
                    errors["base"] = "auth"
                else:
                    errors["base"] = "cannot_connect"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected Speed Dial config error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info[CONF_BASE_URL].casefold())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info[CONF_NAME], data=info)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
