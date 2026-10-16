from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    redis_host: str = "redis"
    redis_port: int = 6379
    # БД Redis для pub/sub-канала уведомлений и хранения истории на пользователя.
    redis_notifications_db: int = 1

    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_booking_created: str = "booking.created"
    kafka_topic_booking_cancelled: str = "booking.cancelled"
    kafka_group_id: str = "notification-service"

    # notification-service только *проверяет* токены публичным ключом (RS256),
    # как и остальные сервисы. Мятить токены умеет только auth-service.
    jwt_public_key_path: str = "/keys/public.pem"
    jwt_algorithm: str = "RS256"

    # Канал Redis pub/sub, в который consumer публикует уведомления, а
    # ws-сервер на него подписан и раздаёт их по WebSocket.
    notifications_channel: str = "notifications"
    # Сколько последних уведомлений хранить на пользователя (история).
    history_size: int = 5

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_notifications_db}"

    @staticmethod
    def history_key(user_id: int) -> str:
        return f"notif:history:{user_id}"


settings = Settings()
