from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_db: str = "analytics"

    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_booking_created: str = "booking.created"
    kafka_topic_booking_cancelled: str = "booking.cancelled"
    kafka_group_id: str = "analytics-service"


settings = Settings()
