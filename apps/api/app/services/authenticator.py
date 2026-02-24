"""
VOLO — Authenticator Vault Service
Stores TOTP/Google Authenticator secrets encrypted in PostgreSQL.
Generates 2FA codes on demand — no copy-paste needed.

Usage flow:
1. User adds a service (e.g., Telegram) with its TOTP secret
2. When Volo needs a 2FA code (e.g., messaging login), it calls get_code()
3. The correct 6-digit code is auto-injected — zero friction

Security:
- TOTP secrets are encrypted at rest using Fernet (AES-128-CBC)
- Encryption key derived from VOLO_VAULT_KEY env var
- Secrets are never returned in plain text via API
"""

import os
import time
from datetime import datetime
from typing import Optional

import pyotp
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.database import async_session, AuthenticatorAccount


def _get_fernet() -> Fernet:
    """Get or create the Fernet encryption instance for the vault."""
    key = os.getenv("VOLO_VAULT_KEY")
    if not key:
        # Auto-generate a key and warn — in production, set VOLO_VAULT_KEY
        key = Fernet.generate_key().decode()
        os.environ["VOLO_VAULT_KEY"] = key
        print(f"⚠️  No VOLO_VAULT_KEY set — generated ephemeral key. Set it in .env for persistence!")
    # Ensure it's bytes
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class AuthenticatorVault:
    """
    TOTP authenticator vault — stores secrets encrypted, generates codes live.
    Integrates with messaging and other services for auto-2FA.
    """

    def __init__(self):
        self._fernet = _get_fernet()

    def _encrypt(self, secret: str) -> str:
        """Encrypt a TOTP secret for storage."""
        return self._fernet.encrypt(secret.encode()).decode()

    def _decrypt(self, encrypted: str) -> str:
        """Decrypt a TOTP secret for code generation."""
        return self._fernet.decrypt(encrypted.encode()).decode()

    async def add_account(
        self,
        user_id: str,
        service: str,
        secret: str,
        label: str = "",
        issuer: str = "",
        digits: int = 6,
        period: int = 30,
        algorithm: str = "SHA1",
        icon: str = "",
    ) -> dict:
        """
        Add a new TOTP account to the vault.

        Args:
            service: Service identifier (e.g., "telegram", "github", "binance")
            secret: The TOTP secret key (base32 encoded, from QR code or manual entry)
            label: Display name (e.g., "Telegram @ballout")
        """
        # Validate the secret is valid base32
        try:
            pyotp.TOTP(secret).now()
        except Exception:
            raise ValueError(f"Invalid TOTP secret — must be valid base32. Got: {secret[:4]}...")

        encrypted = self._encrypt(secret)

        async with async_session() as session:
            # Check for existing account for same service
            result = await session.execute(
                select(AuthenticatorAccount).where(
                    AuthenticatorAccount.user_id == user_id,
                    AuthenticatorAccount.service == service.lower(),
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.encrypted_secret = encrypted
                existing.label = label or existing.label
                existing.issuer = issuer or existing.issuer
                existing.digits = digits
                existing.period = period
                existing.algorithm = algorithm
                if icon:
                    existing.icon = icon
                account_id = existing.id
            else:
                account = AuthenticatorAccount(
                    user_id=user_id,
                    service=service.lower(),
                    label=label or f"{service} 2FA",
                    encrypted_secret=encrypted,
                    issuer=issuer or service,
                    digits=digits,
                    period=period,
                    algorithm=algorithm,
                    icon=icon,
                )
                session.add(account)
                await session.flush()
                account_id = account.id

            await session.commit()

        return {
            "id": account_id,
            "service": service.lower(),
            "label": label or f"{service} 2FA",
            "issuer": issuer or service,
            "message": f"Authenticator added for {service}",
        }

    async def get_code(self, user_id: str, service: str) -> Optional[dict]:
        """
        Generate the current TOTP code for a service.
        This is what gets auto-injected when logging into messaging etc.
        """
        async with async_session() as session:
            result = await session.execute(
                select(AuthenticatorAccount).where(
                    AuthenticatorAccount.user_id == user_id,
                    AuthenticatorAccount.service == service.lower(),
                )
            )
            account = result.scalar_one_or_none()

            if not account:
                return None

            secret = self._decrypt(account.encrypted_secret)
            totp = pyotp.TOTP(
                secret,
                digits=account.digits or 6,
                interval=account.period or 30,
            )
            code = totp.now()
            remaining = account.period - (int(time.time()) % (account.period or 30))

            # Update last_used_at
            account.last_used_at = datetime.utcnow()
            await session.commit()

            return {
                "code": code,
                "service": account.service,
                "label": account.label,
                "remaining_seconds": remaining,
                "period": account.period,
                "digits": account.digits,
            }

    async def get_all_codes(self, user_id: str) -> list[dict]:
        """Get current codes for ALL accounts — like opening Google Authenticator."""
        async with async_session() as session:
            result = await session.execute(
                select(AuthenticatorAccount).where(
                    AuthenticatorAccount.user_id == user_id,
                ).order_by(AuthenticatorAccount.service)
            )
            accounts = result.scalars().all()

            codes = []
            now = int(time.time())
            for account in accounts:
                try:
                    secret = self._decrypt(account.encrypted_secret)
                    totp = pyotp.TOTP(
                        secret,
                        digits=account.digits or 6,
                        interval=account.period or 30,
                    )
                    period = account.period or 30
                    codes.append({
                        "id": account.id,
                        "service": account.service,
                        "label": account.label,
                        "issuer": account.issuer,
                        "code": totp.now(),
                        "remaining_seconds": period - (now % period),
                        "period": period,
                        "digits": account.digits or 6,
                        "icon": account.icon,
                        "last_used_at": account.last_used_at.isoformat() if account.last_used_at else None,
                    })
                except Exception:
                    codes.append({
                        "id": account.id,
                        "service": account.service,
                        "label": account.label,
                        "code": None,
                        "error": "Failed to decrypt — vault key may have changed",
                    })

        return codes

    async def list_accounts(self, user_id: str) -> list[dict]:
        """List all TOTP accounts (without secrets or codes)."""
        async with async_session() as session:
            result = await session.execute(
                select(AuthenticatorAccount).where(
                    AuthenticatorAccount.user_id == user_id,
                ).order_by(AuthenticatorAccount.service)
            )
            return [
                {
                    "id": a.id,
                    "service": a.service,
                    "label": a.label,
                    "issuer": a.issuer,
                    "digits": a.digits,
                    "period": a.period,
                    "icon": a.icon,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "last_used_at": a.last_used_at.isoformat() if a.last_used_at else None,
                }
                for a in result.scalars().all()
            ]

    async def remove_account(self, user_id: str, service: str = "", account_id: str = "") -> bool:
        """Remove a TOTP account from the vault."""
        async with async_session() as session:
            if account_id:
                result = await session.execute(
                    select(AuthenticatorAccount).where(
                        AuthenticatorAccount.id == account_id,
                        AuthenticatorAccount.user_id == user_id,
                    )
                )
            else:
                result = await session.execute(
                    select(AuthenticatorAccount).where(
                        AuthenticatorAccount.user_id == user_id,
                        AuthenticatorAccount.service == service.lower(),
                    )
                )
            account = result.scalar_one_or_none()
            if account:
                await session.delete(account)
                await session.commit()
                return True
        return False

    async def verify_code(self, user_id: str, service: str, code: str) -> bool:
        """Verify a TOTP code against the stored secret. Used for testing setup."""
        async with async_session() as session:
            result = await session.execute(
                select(AuthenticatorAccount).where(
                    AuthenticatorAccount.user_id == user_id,
                    AuthenticatorAccount.service == service.lower(),
                )
            )
            account = result.scalar_one_or_none()
            if not account:
                return False

            secret = self._decrypt(account.encrypted_secret)
            totp = pyotp.TOTP(
                secret,
                digits=account.digits or 6,
                interval=account.period or 30,
            )
            return totp.verify(code)


# Singleton
authenticator_vault = AuthenticatorVault()
