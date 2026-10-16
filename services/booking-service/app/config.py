from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    postgres_user: str = "platform"
    postgres_password: str = "platform_pass"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "booking_db"

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_lock_db: int = 0

    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_booking_created: str = "booking.created"
    kafka_topic_booking_cancelled: str = "booking.cancelled"
    kafka_topic_booking_updated: str = "booking.updated"

    # booking-service only *verifies* tokens, so it holds the public key only.
    # It cannot mint tokens — that power stays with auth-service.
    jwt_public_key_path: str = "/keys/public.pem"
    jwt_algorithm: str = "RS256"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
