import base64

import pytest

from app.modules.email.exceptions import MalformedEmailError
from app.modules.email.parser import parse_gmail_message
from app.modules.email.utils import decode_base64url, telegram_chunks


def encoded(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def message(payload, **extra):
    return {"id": "m1", "threadId": "t1", "internalDate": "1704067200000", "labelIds": ["INBOX", "UNREAD"], "payload": payload, **extra}


def test_base64url_missing_padding() -> None:
    assert decode_base64url(encoded("salom")) == b"salom"


def test_base64url_malformed() -> None:
    with pytest.raises(MalformedEmailError):
        decode_base64url("a")


def test_plain_text_and_encoded_subject() -> None:
    parsed = parse_gmail_message(message({"mimeType": "text/plain", "headers": [{"name": "Subject", "value": "=?utf-8?b?U2Fsb20g8J+Riw==?="}, {"name": "From", "value": "Szymon <s@example.com>"}], "body": {"data": encoded("Body")}}))
    assert parsed.subject == "Salom 👋"
    assert parsed.body_text == "Body"
    assert parsed.from_address == "s@example.com"


def test_html_only_strips_active_content() -> None:
    parsed = parse_gmail_message(message({"mimeType": "text/html", "headers": [], "body": {"data": encoded("<p>Hello</p><script>steal()</script><img src='http://remote'>")}}))
    assert parsed.body_text == "Hello"
    assert "steal" not in parsed.body_text
    assert "remote" not in parsed.body_text


def test_multipart_prefers_plain_and_detects_attachment_without_download() -> None:
    parsed = parse_gmail_message(message({"mimeType": "multipart/mixed", "headers": [], "parts": [{"mimeType": "text/plain", "body": {"data": encoded("Plain")}}, {"mimeType": "text/html", "body": {"data": encoded("<b>HTML</b>")}}, {"mimeType": "application/pdf", "filename": "invoice.pdf", "body": {"attachmentId": "att1", "size": 42}}]}))
    assert parsed.body_text == "Plain"
    assert parsed.attachments[0].attachment_id == "att1"
    assert parsed.attachments[0].size == 42


def test_telegram_chunks_are_bounded_and_lossless_words() -> None:
    value = "word " * 1000
    chunks = telegram_chunks(value, 200)
    assert all(len(chunk) <= 200 for chunk in chunks)
    assert " ".join(chunks).split() == value.split()
