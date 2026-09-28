"""Async Calendar REST transport; official google-auth owns token refresh."""

from typing import Any
from urllib.parse import quote

import httpx

from app.modules.calendar.auth import GoogleTokenProvider
from app.modules.calendar.exceptions import (
    CalendarConflictError,
    CalendarError,
    CalendarEventNotFoundError,
    GoogleCalendarAuthenticationError,
    GoogleCalendarPermissionError,
    GoogleCalendarUnavailableError,
)


class GoogleCalendarClient:
    def __init__(
        self, http: httpx.AsyncClient, tokens: GoogleTokenProvider, calendar_id: str
    ) -> None:
        self.http, self.tokens, self.calendar_id = http, tokens, calendar_id
        self.base = "https://www.googleapis.com/calendar/v3"
        self.events = f"/calendars/{quote(calendar_id, safe='')}/events"

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        etag: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {await self.tokens.access_token()}"}
        if etag:
            headers["If-Match"] = etag
        try:
            response = await self.http.request(
                method, self.base + path, params=params, json=body, headers=headers
            )
        except httpx.RequestError:
            raise GoogleCalendarUnavailableError(
                "Google temporarily unavailable. Try later."
            ) from None
        status = response.status_code
        if status == 401:
            self.tokens.invalidate()
            raise GoogleCalendarAuthenticationError("Google authorization expired. Reconnect.")
        if status == 403:
            try:
                reasons = str(response.json().get("error", {}).get("errors", []))
            except ValueError:
                reasons = ""
            if "rateLimitExceeded" in reasons or "userRateLimitExceeded" in reasons:
                raise GoogleCalendarUnavailableError("Google rate limit reached. Try later.")
            raise GoogleCalendarPermissionError("Calendar permission denied.")
        if status in (404, 410):
            raise CalendarEventNotFoundError("Calendar event not found.")
        if status in (409, 412):
            raise CalendarConflictError(
                "Event changed or action already submitted. Refresh the list."
            )
        if status == 429 or status >= 500:
            raise GoogleCalendarUnavailableError(
                "Google temporarily unavailable or rate limited. Try later."
            )
        if status >= 400:
            raise CalendarError("Google rejected the calendar request.")
        if status == 204:
            return {}
        try:
            return response.json()
        except ValueError:
            raise GoogleCalendarUnavailableError("Invalid Calendar response. Try later.") from None

    async def list_events(self, start: str, end: str | None, limit: int) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        params: dict[str, Any] = {
            "timeMin": start,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": min(limit, 250),
        }
        if end:
            params["timeMax"] = end
        while len(result) < limit:
            page = await self.request("GET", self.events, params=params)
            result.extend(
                item for item in page.get("items", []) if item.get("status") != "cancelled"
            )
            if not page.get("nextPageToken"):
                break
            params["pageToken"] = page["nextPageToken"]
        return result[:limit]

    async def create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", self.events, body=payload, params={"sendUpdates": "none"})

    async def get_event(self, event_id: str) -> dict[str, Any]:
        return await self.request("GET", f"{self.events}/{quote(event_id, safe='')}")

    async def update_event(
        self, event_id: str, payload: dict[str, Any], etag: str
    ) -> dict[str, Any]:
        return await self.request(
            "PATCH",
            f"{self.events}/{quote(event_id, safe='')}",
            body=payload,
            etag=etag,
            params={"sendUpdates": "none"},
        )

    async def delete_event(self, event_id: str, etag: str) -> None:
        await self.request(
            "DELETE",
            f"{self.events}/{quote(event_id, safe='')}",
            etag=etag,
            params={"sendUpdates": "none"},
        )

    async def free_busy(self, start: str, end: str, timezone: str) -> dict[str, Any]:
        return await self.request(
            "POST",
            "/freeBusy",
            body={
                "timeMin": start,
                "timeMax": end,
                "timeZone": timezone,
                "items": [{"id": self.calendar_id}],
            },
        )
