from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.modules.calendar.client import GoogleCalendarClient
from app.modules.calendar.exceptions import (
    CalendarConflictError,
    CalendarEventNotFoundError,
    GoogleCalendarAuthenticationError,
    GoogleCalendarPermissionError,
    GoogleCalendarUnavailableError,
)


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, GoogleCalendarAuthenticationError),
        (403, GoogleCalendarPermissionError),
        (404, CalendarEventNotFoundError),
        (429, GoogleCalendarUnavailableError),
        (503, GoogleCalendarUnavailableError),
        (412, CalendarConflictError),
    ],
)
async def test_safe_error_mapping(status, error) -> None:
    token = Mock(access_token=AsyncMock(return_value="private-access"))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, json={"error": {"message": "secret-data"}})
        )
    ) as http:
        client = GoogleCalendarClient(http, token, "primary")
        with pytest.raises(error) as caught:
            await client.get_event("abc")
        assert "secret-data" not in str(caught.value)
        assert "private-access" not in str(caught.value)


async def test_insert_payload_and_patch_precondition() -> None:
    requests = []

    def reply(request):
        requests.append(request)
        return httpx.Response(200, json={"id": "abc"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as http:
        client = GoogleCalendarClient(
            http, Mock(access_token=AsyncMock(return_value="test")), "primary"
        )
        await client.create_event({"summary": "Test"})
        assert requests[0].method == "POST" and b"Test" in requests[0].content
        await client.update_event("abc", {"summary": "Changed"}, '"v1"')
        assert requests[1].method == "PATCH"
        assert requests[1].headers["If-Match"] == '"v1"'
        await client.delete_event("abc", '"v1"')
        assert requests[2].headers["If-Match"] == '"v1"'


async def test_pagination_and_recurring_expansion() -> None:
    requests = []

    def reply(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "items": [{"id": str(len(requests))}],
                **({"nextPageToken": "next"} if len(requests) == 1 else {}),
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as http:
        client = GoogleCalendarClient(
            http, Mock(access_token=AsyncMock(return_value="test")), "primary"
        )
        assert len(await client.list_events("2026-09-25T00:00:00Z", None, 10)) == 2
    assert requests[0].url.params["singleEvents"] == "true"
    assert requests[0].url.params["orderBy"] == "startTime"
    assert requests[1].url.params["pageToken"] == "next"
