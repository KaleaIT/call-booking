from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    postgres_user: str = "platform"
    postgres_password: str = "platform_pass"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "auth_db"

    # Asymmetric JWT (RS256): auth-service is the only holder of the private
    # key and is the sole token issuer. Every other service verifies with the
    # public key alone — a leak in any consumer cannot forge tokens.
    jwt_private_key_path: str = "/keys/private.pem"
    jwt_public_key_path: str = "/keys/public.pem"
    jwt_algorithm: str = "RS256"
    jwt_expire_minutes: int = 60

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
