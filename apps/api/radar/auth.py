from fastapi import Header, HTTPException, Request, status

from radar.config import get_settings


async def require_token(
    request: Request,
    x_radar_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()

    if settings.allowed_ips:
        client_host = request.client.host if request.client else ""
        if client_host not in settings.allowed_ips:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="IP not allowed")

    if x_radar_token != settings.radar_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid radar token")
