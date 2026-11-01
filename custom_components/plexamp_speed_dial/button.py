"""Button entities — one per speed-dial favorite."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SpeedDialApiError
from .const import ATTR_DESCRIPTION, ATTR_FAVORITE_ID, ATTR_LABEL, DOMAIN
from .coordinator import SpeedDialCoordinator, speed_dial_display_name

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up speed-dial buttons from a config entry."""
    stored = hass.data[DOMAIN][entry.entry_id]
    coordinator: SpeedDialCoordinator = stored["coordinator"]

    known_ids: set[int] = set()

    def _entities_from_data() -> list[SpeedDialFavoriteButton]:
        entities: list[SpeedDialFavoriteButton] = []
        for row in coordinator.data or []:
            try:
                fav_id = int(row["id"])
            except (KeyError, TypeError, ValueError):
                continue
            if fav_id in known_ids:
                continue
            known_ids.add(fav_id)
            entities.append(SpeedDialFavoriteButton(coordinator, entry, row))
        return entities

    async_add_entities(_entities_from_data())

    @callback
    def _on_update() -> None:
        new_entities = _entities_from_data()
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_on_update))


class SpeedDialFavoriteButton(CoordinatorEntity[SpeedDialCoordinator], ButtonEntity):
    """Press to play a speed-dial favorite."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: SpeedDialCoordinator,
        entry: ConfigEntry,
        favorite: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._favorite_id = int(favorite["id"])
        self._attr_unique_id = f"{entry.entry_id}_favorite_{self._favorite_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Plexamp Speed Dial",
            model="Speed Dial",
        )

    @property
    def name(self) -> str:
        favorite = self.favorite
        if favorite is None:
            return f"Speed dial {self._favorite_id}"
        return speed_dial_display_name(favorite)

    @property
    def suggested_object_id(self) -> str:
        favorite = self.favorite or {}
        label = str(favorite.get("label") or "").strip()
        return label or f"speed_dial_{self._favorite_id}"

    @property
    def favorite(self) -> dict[str, Any] | None:
        return self.coordinator.favorite_by_id(self._favorite_id)

    @property
    def available(self) -> bool:
        return super().available and self.favorite is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        fav = self.favorite or {}
        return {
            ATTR_FAVORITE_ID: self._favorite_id,
            ATTR_LABEL: fav.get("label"),
            ATTR_DESCRIPTION: fav.get("description") or "",
        }

    async def async_press(self) -> None:
        """Play this favorite."""
        client = self.hass.data[DOMAIN][self._entry.entry_id]["client"]
        try:
            await client.async_play_favorite(self._favorite_id)
        except SpeedDialApiError as err:
            raise HomeAssistantError(str(err)) from err
        _LOGGER.debug("Played speed dial id=%s", self._favorite_id)
