from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Usage Billing Engine"
    environment: str = "local"
    secret_key: str = "dev-only-change-me"
    database_url: str = "sqlite:///./billing.db"
    redis_url: str = "redis://localhost:6379/0"
    outbox_sync: bool = True
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = "whsec_test_secret"
    payment_provider: str = "mock"
    cors_origins: str = "http://localhost:5173"
    feature_shadow_pricing: bool = False
    access_token_expire_minutes: int = 60 * 24

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
