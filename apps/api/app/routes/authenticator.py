"""
VOLO — Authenticator Routes
Built-in Google Authenticator / TOTP vault.
Add your 2FA secrets once, Volo auto-fills codes everywhere.

Key endpoints:
  POST   /api/authenticator/add        — Add a TOTP account
  GET    /api/authenticator/codes       — Get all current codes (like opening GAuth)
  GET    /api/authenticator/code/{svc}  — Get code for a specific service
  GET    /api/authenticator/accounts    — List accounts (no secrets/codes)
  DELETE /api/authenticator/{svc}       — Remove a TOTP account
  POST   /api/authenticator/verify      — Test that a code matches
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.auth import get_current_user, CurrentUser
from app.services.authenticator import authenticator_vault

router = APIRouter()


class AddAccountRequest(BaseModel):
    service: str                     # "telegram", "github", "binance", etc.
    secret: str                      # Base32 TOTP secret from QR code or manual
    label: Optional[str] = ""        # "Telegram @ballout"
    issuer: Optional[str] = ""       # "Telegram"
    digits: int = 6                  # Usually 6, some services use 8
    period: int = 30                 # Usually 30s
    algorithm: str = "SHA1"          # SHA1, SHA256, SHA512
    icon: Optional[str] = ""         # Icon URL


class VerifyCodeRequest(BaseModel):
    service: str
    code: str


@router.post("/authenticator/add")
async def add_authenticator_account(body: AddAccountRequest, current_user: CurrentUser = Depends(get_current_user)):
    """
    Add a TOTP / Google Authenticator account to Volo's vault.

    Get the secret from your service's 2FA setup page:
    - Scan the QR code to get the secret, OR
    - Copy the "manual setup key" / "secret key" text

    The secret is encrypted at rest — never stored in plain text.
    """
    try:
        result = await authenticator_vault.add_account(
            user_id=current_user.user_id,
            service=body.service,
            secret=body.secret.replace(" ", "").upper(),
            label=body.label or "",
            issuer=body.issuer or "",
            digits=body.digits,
            period=body.period,
            algorithm=body.algorithm,
            icon=body.icon or "",
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/authenticator/codes")
async def get_all_codes(current_user: CurrentUser = Depends(get_current_user)):
    """
    Get current TOTP codes for ALL accounts.
    Like opening Google Authenticator — shows all your codes at once.
    Each code includes remaining seconds before refresh.
    """
    codes = await authenticator_vault.get_all_codes(user_id=current_user.user_id)
    return {"codes": codes, "total": len(codes)}


@router.get("/authenticator/code/{service}")
async def get_code(service: str, current_user: CurrentUser = Depends(get_current_user)):
    """
    Get the current TOTP code for a specific service.
    This is what Volo calls internally when auto-filling 2FA.

    Example: GET /api/authenticator/code/telegram
    Returns: {"code": "482901", "remaining_seconds": 17, ...}
    """
    result = await authenticator_vault.get_code(user_id=current_user.user_id, service=service)
    if not result:
        raise HTTPException(
            404,
            f"No authenticator found for '{service}'. "
            f"Add one with POST /api/authenticator/add",
        )
    return result


@router.get("/authenticator/accounts")
async def list_accounts(current_user: CurrentUser = Depends(get_current_user)):
    """List all TOTP accounts in the vault (no secrets or codes)."""
    accounts = await authenticator_vault.list_accounts(user_id=current_user.user_id)
    return {"accounts": accounts, "total": len(accounts)}


@router.delete("/authenticator/{service}")
async def remove_account(service: str, current_user: CurrentUser = Depends(get_current_user)):
    """Remove a TOTP account from the vault."""
    removed = await authenticator_vault.remove_account(
        user_id=current_user.user_id, service=service
    )
    if not removed:
        raise HTTPException(404, f"No authenticator found for '{service}'")
    return {"success": True, "message": f"Authenticator for {service} removed."}


@router.post("/authenticator/verify")
async def verify_code(body: VerifyCodeRequest, current_user: CurrentUser = Depends(get_current_user)):
    """
    Verify a TOTP code against the stored secret.
    Useful for testing that the setup was done correctly.
    """
    valid = await authenticator_vault.verify_code(
        user_id=current_user.user_id,
        service=body.service,
        code=body.code,
    )
    return {"valid": valid, "service": body.service}
