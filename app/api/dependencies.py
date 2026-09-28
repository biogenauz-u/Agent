from fastapi import Request

from app.core.application import ApplicationContext


def application_context(request: Request) -> ApplicationContext:
    return request.app.state.context
