"""API key check for protected routes.

If GROUNDTRUTH_API_KEY isn't set in .env, every protected request is
rejected -- deliberately, so the API can't accidentally go live wide open.
"""
from fastapi import Header, HTTPException

from .config import settings


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key header")
