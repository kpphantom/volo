"""
VOLO — Application Config
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Volo"
    app_env: str = "development"
    app_port: int = 8000
    app_secret_key: str = "change-me"
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://volo:volo@localhost:5432/volo"
    redis_url: str = "redis://localhost:6379"

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_model: str = "claude-sonnet-4-20250514"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # OAuth Providers
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = ""
    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    twitter_redirect_uri: str = ""

    # Authenticator Vault
    volo_vault_key: str = ""

    # White Label
    default_tenant_id: str = "volo-default"
    default_tenant_name: str = "Volo"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
