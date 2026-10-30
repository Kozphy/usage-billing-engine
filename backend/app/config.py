"""Application settings loaded from environment / ``.env``."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the usage billing engine.

    Attributes:
        app_name: Service display name.
        environment: Deployment label (for example ``local`` or ``ci``).
        secret_key: JWT signing secret (never commit real values).
        database_url: SQLAlchemy URL (SQLite or Postgres).
        redis_url: Optional Redis URL reserved for future async work.
        outbox_sync: When true, drain outbox inline in the API process.
        outbox_max_attempts: Bounded retry limit before terminal failure.
        outbox_backoff_seconds: Linear backoff base between retries.
        worker_id: Default claim identity for outbox processing.
        stripe_secret_key: Stripe secret; empty means mock-only path.
        stripe_webhook_secret: HMAC secret for Stripe-like webhook signatures.
        payment_provider: ``mock`` or ``stripe``.
        mock_payment_timeout_rate: Probability of simulated provider timeout.
        cors_origins: Comma-separated browser origins.
        feature_shadow_pricing: Feature flag reserved for shadow pricing UX.
        access_token_expire_minutes: JWT lifetime.
        log_level: Root log level name.
        shadow_expected_tolerance: Absolute money tolerance for ``match``.
    """

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
        """Parse ``cors_origins`` into a list of origin strings.

        Returns:
            Non-empty trimmed origin URLs.
        """
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @property
    def is_postgres(self) -> bool:
        """Return whether the configured database URL targets PostgreSQL.

        Returns:
            ``True`` when ``database_url`` starts with ``postgresql``.
        """
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance.

    Returns:
        Process-wide ``Settings`` object.
    """
    return Settings()
