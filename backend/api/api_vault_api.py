"""
API Vault Endpoints — Central secure access point for all API keys.

Provides:
- Status of all configured providers (masked keys)
- Connectivity verification per provider
- Key rotation with audit trail
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault", tags=["API Vault"])


class RotateKeyRequest(BaseModel):
    provider: str
    new_key: str


@router.get("/status")
async def vault_status():
    """Get status of all API providers — key presence, masked key, model."""
    from security.api_vault import get_vault
    vault = get_vault()
    return {"providers": vault.get_status()}


@router.get("/verify")
async def verify_all():
    """Verify connectivity to all providers."""
    from security.api_vault import get_vault
    vault = get_vault()
    return vault.verify_all()


@router.get("/verify/{provider}")
async def verify_provider(provider: str):
    """Verify connectivity to a specific provider."""
    from security.api_vault import get_vault
    vault = get_vault()
    result = vault.verify_provider(provider)
    return result


@router.post("/rotate")
async def rotate_key(req: RotateKeyRequest):
    """Rotate an API key with audit trail."""
    from security.api_vault import get_vault
    vault = get_vault()
    result = vault.rotate_key(req.provider, req.new_key)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
