from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    WEBHOOK_URL: str = ""
    DATABASE_URL: str = ""

    TONNEL_AUTH_DATA: str = ""
    MRKT_AUTH_DATA: str = ""
    PORTALS_AUTH_DATA: str = ""
    FRAGMENT_AUTH_DATA: str = ""

    GIFT_ASSET_API_KEY: str = ""

    HOST: str = "0.0.0.0"
    PORT: int = 8080

    SCAN_INTERVAL: int = 7
    SELF_PING_INTERVAL: int = 600
    LISTINGS_TTL: int = 3600
    MAX_ALERTS_KEPT: int = 200
    REQUEST_TIMEOUT: float = 15.0
    MAX_RETRIES: int = 3
    LOG_LEVEL: str = "INFO"

    ENVIRONMENT: str = "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
