from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any

from app.modules.email.schemas import AttachmentMetadata, EmailContent
from app.modules.email.utils import decode_base64url


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg"}:
            self.ignored += 1
        elif not self.ignored and tag in {"p", "div", "br", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)


def html_to_text(value: str) -> str:
    parser = _HTMLText()
    parser.feed(value)
    return "\n".join(line.strip() for line in unescape("".join(parser.parts)).splitlines() if line.strip())


def _header(headers: list[dict[str, str]], name: str) -> str:
    raw = next((item.get("value", "") for item in headers if item.get("name", "").lower() == name.lower()), "")
    try:
        return str(make_header(decode_header(raw)))
    except (LookupError, UnicodeError):
        return raw


def _walk(part: dict[str, Any]) -> tuple[list[str], list[str], list[AttachmentMetadata]]:
    plain: list[str] = []
    html: list[str] = []
    attachments: list[AttachmentMetadata] = []
    filename = str(part.get("filename") or "")
    body = part.get("body") or {}
    attachment_id = body.get("attachmentId")
    mime = str(part.get("mimeType") or "application/octet-stream")
    if filename or attachment_id:
        attachments.append(AttachmentMetadata(filename=filename or "attachment", mime_type=mime, size=int(body.get("size") or 0), attachment_id=attachment_id))
    elif body.get("data") and mime in {"text/plain", "text/html"}:
        value = decode_base64url(str(body["data"])).decode("utf-8", errors="replace")
        (plain if mime == "text/plain" else html).append(value)
    for child in part.get("parts") or []:
        child_plain, child_html, child_attachments = _walk(child)
        plain.extend(child_plain)
        html.extend(child_html)
        attachments.extend(child_attachments)
    return plain, html, attachments


def parse_gmail_message(message: dict[str, Any]) -> EmailContent:
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []
    plain, html, attachments = _walk(payload)
    sender_name, sender_address = parseaddr(_header(headers, "From"))
    date_value = _header(headers, "Date")
    try:
        received = parsedate_to_datetime(date_value).astimezone(UTC) if date_value else None
    except (TypeError, ValueError, OverflowError):
        received = None
    if received is None:
        received = datetime.fromtimestamp(int(message.get("internalDate", "0")) / 1000, UTC)
    body = "\n\n".join(item.strip() for item in plain if item.strip())
    if not body:
        body = html_to_text("\n".join(html))
    return EmailContent(
        gmail_message_id=str(message["id"]),
        gmail_thread_id=str(message.get("threadId") or message["id"]),
        history_id=str(message["historyId"]) if message.get("historyId") else None,
        from_address=sender_address,
        from_name=sender_name or None,
        to_addresses=[address for _, address in getaddresses([_header(headers, "To")])],
        cc_addresses=[address for _, address in getaddresses([_header(headers, "Cc")])],
        subject=_header(headers, "Subject") or "(No subject)",
        snippet=str(message.get("snippet") or ""),
        received_at=received,
        labels=[str(label) for label in message.get("labelIds") or []],
        body_text=body,
        attachments=attachments,
    )
