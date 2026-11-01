"""Data update coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SpeedDialApiClient, SpeedDialApiError
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


def speed_dial_display_name(favorite: dict[str, Any]) -> str:
    """Favorite label plus player, speakers, and volumes."""
    label = str(favorite.get("label") or "").strip()
    description = str(favorite.get("description") or "").strip()
    if not label:
        label = f"Speed dial {favorite.get('id')}"
    if description:
        return f"{label} — {description}"
    return label


class SpeedDialCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Fetch speed-dial favorites on setup and every five minutes."""

    def __init__(self, hass: HomeAssistant, client: SpeedDialApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            return await self.client.async_list_speed_dials()
        except SpeedDialApiError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Speed Dial request failed: {err}") from err

    def favorite_by_id(self, favorite_id: int) -> dict[str, Any] | None:
        for row in self.data or []:
            if int(row.get("id", -1)) == favorite_id:
                return row
        return None

    def favorite_by_label(self, label: str) -> dict[str, Any] | None:
        want = label.strip().casefold()
        matches = [row for row in (self.data or []) if str(row.get("label", "")).strip().casefold() == want]
        if not matches:
            return None
        if len(matches) > 1:
            _LOGGER.warning("Multiple speed dials match label %r; using id=%s", label, matches[0].get("id"))
        return matches[0]
