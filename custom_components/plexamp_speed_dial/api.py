"""Async HTTP client for the Plexamp Speed Dial API."""

from __future__ import annotations

from typing import Any

import aiohttp


class SpeedDialApiError(Exception):
    """Raised when the Speed Dial API returns an error."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class SpeedDialApiClient:
    """Thin client for /api/v1 speed-dial endpoints."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str) -> None:
        self._session = session
        self._base = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self._base}/api/v1{path}"

    async def async_list_speed_dials(self) -> list[dict[str, Any]]:
        async with self._session.get(self._url("/speed-dial"), timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise SpeedDialApiError(
                    f"List speed dials failed ({resp.status}): {text[:200]}",
                    status=resp.status,
                )
            data = await resp.json(content_type=None)
            if not isinstance(data, list):
                raise SpeedDialApiError("Unexpected speed-dial list payload")
            return data

    async def async_play_favorite(self, favorite_id: int) -> None:
        async with self._session.post(
            self._url(f"/speed-dial/{favorite_id}/play"),
            timeout=aiohttp.ClientTimeout(total=90),
        ) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise SpeedDialApiError(
                    f"Play favorite {favorite_id} failed ({resp.status}): {text[:200]}",
                    status=resp.status,
                )

    async def async_test_connection(self) -> list[dict[str, Any]]:
        """Validate base URL by listing speed dials."""
        return await self.async_list_speed_dials()
