from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Usage Billing Engine"
    environment: str = "local"
    secret_key: str = "dev-only-change-me"
    database_url: str = "sqlite:///./billing.db"
    redis_url: str = "redis://localhost:6379/0"
    # When true, API process drains outbox inline (handy for unit tests).
    # Compose/worker demos set this false so a durable worker owns processing.
    outbox_sync: bool = True
    outbox_max_attempts: int = 5
    outbox_backoff_seconds: int = 2
    worker_id: str = "api"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = "whsec_test_secret"
    # mock (deterministic fake) | stripe (test-mode when key present)
    payment_provider: str = "mock"
    # Simulated fake-provider timeout rate for offline failure demos (0–1).
    mock_payment_timeout_rate: float = 0.0
    cors_origins: str = "http://localhost:5173"
    feature_shadow_pricing: bool = False
    access_token_expire_minutes: int = 60 * 24
    log_level: str = "INFO"
    # Absolute Decimal tolerance for classifying shadow deltas as expected.
    # Unexpected means |delta| > tolerance and not in expected_delta_allowlist.
    shadow_expected_tolerance: str = "0.0000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()
