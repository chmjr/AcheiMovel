from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from radar.auth import require_token
from radar.db import get_db
from radar.schemas import ManualPropertyCreate, ManualPropertyResponse
from radar.services.properties import create_manual_property

router = APIRouter(prefix="/properties", tags=["properties"], dependencies=[Depends(require_token)])


@router.post(
    "/manual",
    response_model=ManualPropertyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_property_endpoint(
    payload: ManualPropertyCreate,
    db: Session = Depends(get_db),
) -> ManualPropertyResponse:
    return create_manual_property(db, payload)
