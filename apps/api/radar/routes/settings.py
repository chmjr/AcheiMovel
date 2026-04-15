from fastapi import APIRouter, Depends

from radar.auth import require_token
from radar.schemas import InvestorProfile

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_token)])

_PROFILE = InvestorProfile()


@router.get("", response_model=InvestorProfile)
async def get_settings() -> InvestorProfile:
    return _PROFILE


@router.put("", response_model=InvestorProfile)
async def update_settings(profile: InvestorProfile) -> InvestorProfile:
    global _PROFILE
    _PROFILE = profile
    return _PROFILE
