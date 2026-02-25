"""
VOLO — Application Config
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "Volo"
    app_env: str = "development"
    app_port: int = 8000
    app_secret_key: str
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://volo:volo@localhost:5432/volo"
    redis_url: str = "redis://localhost:6379"

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_model: str = "claude-sonnet-4-20250514"

    # Auth
    jwt_secret: str
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

    # Social OAuth (Instagram, TikTok, Facebook)
    instagram_client_id: str = ""
    instagram_client_secret: str = ""
    instagram_redirect_uri: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_redirect_uri: str = ""

    # Messaging Platforms
    telegram_bot_token: str = ""
    whatsapp_api_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_business_token: str = ""
    whatsapp_business_phone_id: str = ""
    signal_api_url: str = ""
    discord_bot_token: str = ""
    slack_bot_token: str = ""
    slack_app_token: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_signing_secret: str = ""
    slack_redirect_uri: str = ""

    # Plaid (Banking)
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"  # sandbox, development, production

    # Authenticator Vault
    volo_vault_key: str = ""

    # White Label
    default_tenant_id: str = "volo-default"
    default_tenant_name: str = "Volo"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
