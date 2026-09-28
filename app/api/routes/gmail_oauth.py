import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.api.dependencies import application_context
from app.core.application import ApplicationContext
from app.modules.email.exceptions import GmailError

router = APIRouter(prefix="/oauth/gmail")
Context = Annotated[ApplicationContext, Depends(application_context)]
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"}


@router.get("/start", response_model=None)
async def start(context: Context, ticket: str = "") -> PlainTextResponse | RedirectResponse:
    if context.email is None or not 20 <= len(ticket) <= 128:
        return PlainTextResponse("Invalid connection link.", status_code=400, headers=HEADERS)
    browser = secrets.token_urlsafe(32)
    try:
        url = await context.email.oauth.begin(ticket, browser)
    except GmailError as error:
        return PlainTextResponse(str(error), status_code=400, headers=HEADERS)
    response = RedirectResponse(url, status_code=303, headers=HEADERS)
    response.set_cookie("gmail_oauth", browser, max_age=600, httponly=True, samesite="lax", secure=context.email.oauth.redirect_uri.startswith("https:"), path="/oauth/gmail")
    return response


@router.get("/callback")
async def callback(request: Request, context: Context, state: str = "", code: str = "") -> PlainTextResponse:
    if context.email is None or not 20 <= len(state) <= 128 or len(code) > 4096:
        return PlainTextResponse("Invalid OAuth callback.", status_code=400, headers=HEADERS)
    try:
        await context.email.oauth.callback(state, code, request.cookies.get("gmail_oauth", ""))
        response = PlainTextResponse("Gmail connected. You may return to Telegram.", headers=HEADERS)
    except GmailError as error:
        response = PlainTextResponse(str(error), status_code=400, headers=HEADERS)
    response.delete_cookie("gmail_oauth", path="/oauth/gmail")
    return response
