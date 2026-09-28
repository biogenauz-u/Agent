import httpx
import pytest

from app.modules.email.client import (
    GMAIL_READONLY_SCOPE,
    GMAIL_SCOPES,
    GMAIL_SEND_SCOPE,
    GmailClient,
)
from app.modules.email.exceptions import (
    GmailAuthenticationError,
    GmailMessageNotFoundError,
    GmailPermissionError,
    GmailRateLimitError,
)


class Tokens:
    async def access_token(self) -> str:
        return "not-a-real-token"


def client(status=200, payload=None, capture=None):
    async def handler(request):
        if capture is not None:
            capture.append(request)
        return httpx.Response(status, json=payload or {})

    return GmailClient(httpx.AsyncClient(transport=httpx.MockTransport(handler)), Tokens())


def test_scope_is_least_privilege_read_and_send() -> None:
    assert GMAIL_SCOPES == [GMAIL_READONLY_SCOPE, GMAIL_SEND_SCOPE]
    assert all("modify" not in scope for scope in GMAIL_SCOPES)


async def test_list_request() -> None:
    requests = []
    gmail = client(capture=requests)
    await gmail.list_messages(query="from:test", limit=12)
    assert requests[0].url.params["q"] == "from:test"
    assert requests[0].url.params["maxResults"] == "12"
    await gmail.http.aclose()


async def test_fetch_request_never_requests_attachment() -> None:
    requests = []
    gmail = client(capture=requests)
    await gmail.get_message("m1")
    assert requests[0].url.path.endswith("/messages/m1")
    assert requests[0].url.params["format"] == "full"
    assert "attachments" not in requests[0].url.path
    await gmail.http.aclose()


async def test_send_request_contains_safe_mime_and_thread() -> None:
    requests = []
    gmail = client(payload={"id": "sent-1"}, capture=requests)
    assert (
        await gmail.send_message("person@example.com", "Re: Hello", "Thanks", "thread-1")
        == "sent-1"
    )
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path.endswith("/messages/send")
    payload = __import__("json").loads(request.content)
    assert payload["threadId"] == "thread-1"
    assert "person@example.com" not in payload["raw"]
    await gmail.http.aclose()


@pytest.mark.parametrize(
    "status,error",
    [
        (401, GmailAuthenticationError),
        (403, GmailPermissionError),
        (404, GmailMessageNotFoundError),
        (429, GmailRateLimitError),
    ],
)
async def test_safe_error_mapping(status, error) -> None:
    gmail = client(status)
    with pytest.raises(error):
        await gmail.get_message("m1")
    await gmail.http.aclose()
