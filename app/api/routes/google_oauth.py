import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.api.dependencies import application_context
from app.core.application import ApplicationContext
from app.core.logging import report_error
from app.modules.calendar.exceptions import CalendarError

router = APIRouter(prefix="/oauth/google")
Context = Annotated[ApplicationContext, Depends(application_context)]
HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


@router.get("/start", response_model=None)
async def start(context: Context, ticket: str = "") -> PlainTextResponse | RedirectResponse:
    assert context.calendar is not None
    if not 20 <= len(ticket) <= 128:
        return PlainTextResponse("Invalid connection link.", status_code=400, headers=HEADERS)
    browser = secrets.token_urlsafe(32)
    try:
        url = await context.calendar.oauth.begin(ticket, browser)
    except CalendarError as error:
        return PlainTextResponse(str(error), status_code=400, headers=HEADERS)
    except Exception as error:  # noqa: BLE001 - public OAuth boundary never renders backend errors
        report_error(logging.getLogger(__name__), error)
        return PlainTextResponse(
            "Connection unavailable. Try again later.", status_code=503, headers=HEADERS
        )
    response = RedirectResponse(url, status_code=303, headers=HEADERS)
    response.set_cookie(
        "calendar_oauth",
        browser,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=(context.settings.google_redirect_uri or "").startswith("https:"),
        path="/oauth/google",
    )
    return response


@router.get("/callback")
async def callback(
    request: Request, context: Context, state: str = "", code: str = ""
) -> PlainTextResponse:
    assert context.calendar is not None
    if not 20 <= len(state) <= 128 or len(code) > 4096:
        return PlainTextResponse("Invalid OAuth callback.", status_code=400, headers=HEADERS)
    try:
        await context.calendar.oauth.callback(
            state, code, request.cookies.get("calendar_oauth", "")
        )
        response = PlainTextResponse(
            "Google Calendar connected. You may return to Telegram.", headers=HEADERS
        )
    except CalendarError as error:
        response = PlainTextResponse(str(error), status_code=400, headers=HEADERS)
    except Exception as error:  # noqa: BLE001 - public OAuth boundary never renders backend errors
        report_error(logging.getLogger(__name__), error)
        response = PlainTextResponse(
            "Connection unavailable. Use /google_connect again.", status_code=503, headers=HEADERS
        )
    response.delete_cookie("calendar_oauth", path="/oauth/google")
    return response
