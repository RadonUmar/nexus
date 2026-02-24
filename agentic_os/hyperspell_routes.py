from __future__ import annotations

from fastapi import APIRouter, HTTPException

from hyperspell_integration import (
    IntegrationInfo,
    UserInfo,
    UserTokenRequest,
    UserTokenResponse,
    get_hyperspell_client,
)
from .logging import get_logger


logger = get_logger(__name__)
router = APIRouter()


@router.post("/api/hyperspell/user-token", response_model=UserTokenResponse)
async def generate_user_token(request: UserTokenRequest):
    try:
        client = get_hyperspell_client()
        token = client.generate_user_token(request.user_id)

        return UserTokenResponse(token=token, user_id=request.user_id)
    except Exception as exc:
        logger.error("Error generating user token: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hyperspell/integrations")
async def list_integrations():
    try:
        client = get_hyperspell_client()
        integrations = client.list_integrations()
        return {"success": True, "integrations": integrations}
    except Exception as exc:
        logger.error("Error listing integrations: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hyperspell/user/{user_id}")
async def get_user_info(user_id: str):
    try:
        client = get_hyperspell_client()
        user_token = client.generate_user_token(user_id)
        user_info = client.get_user_info(user_token)

        return {"success": True, "user": user_info}
    except Exception as exc:
        logger.error("Error getting user info: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/hyperspell/integration-link")
async def get_integration_link(request: dict):
    try:
        integration_id = request.get("integration_id")
        user_id = request.get("user_id", "default_user")
        redirect_uri = request.get("redirect_uri")

        if not integration_id:
            raise HTTPException(status_code=400, detail="integration_id is required")

        client = get_hyperspell_client()
        user_token = client.generate_user_token(user_id)
        link = client.get_integration_link(integration_id, user_token, redirect_uri)

        return {"success": True, "link": link, "integration_id": integration_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error generating integration link: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
