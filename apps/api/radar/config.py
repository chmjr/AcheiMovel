from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    app_name: str = "Radar Imobiliario Floripa"
    api_prefix: str = "/api/v1"
    radar_api_token: str = Field(default="dev-token", alias="RADAR_API_TOKEN")
    radar_allowed_ips: str = Field(default="", alias="RADAR_ALLOWED_IPS")
    database_url: str = Field(
        default="postgresql+psycopg://radar:radar@localhost:5432/radar",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    alert_email_to: str = Field(default="", alias="ALERT_EMAIL_TO")

    @property
    def allowed_ips(self) -> set[str]:
        return {ip.strip() for ip in self.radar_allowed_ips.split(",") if ip.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
