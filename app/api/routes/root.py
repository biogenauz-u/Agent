from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RootResponse(BaseModel):
    name: str = "Personal AI Assistant"
    status: str = "running"


@router.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse()
