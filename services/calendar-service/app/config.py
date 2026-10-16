from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    postgres_user: str = "platform"
    postgres_password: str = "platform_pass"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "calendar_db"

    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_booking_created: str = "booking.created"
    kafka_topic_booking_cancelled: str = "booking.cancelled"
    kafka_topic_booking_updated: str = "booking.updated"
    kafka_group_id: str = "calendar-service"

    # ── Google OAuth / Calendar ─────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    # Must EXACTLY match an "Authorized redirect URI" in the Google OAuth
    # client. Through the gateway: http://localhost:8080/api/calendar/google/callback
    google_redirect_uri: str = "http://localhost:8080/api/calendar/google/callback"
    # Where to bounce the user back after a successful connect (the popup just
    # closes itself, so this is only a fallback).
    frontend_url: str = "http://localhost:8080"

    # auth-service is queried to resolve participant email + name for events.
    auth_service_url: str = "http://auth-service:8001"

    # Verifies tokens issued by auth-service (RS256, public key only) so the
    # OAuth endpoints know which user is connecting.
    jwt_public_key_path: str = "/keys/public.pem"
    jwt_algorithm: str = "RS256"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
