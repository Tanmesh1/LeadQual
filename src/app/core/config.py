from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Lead Qualification Platform"
    app_env: str = "local"
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    log_level: str = "INFO"
    log_format: str = "json"
    api_v1_prefix: str = "/api/v1"
    lead_scoring_config_path: str = "configs/lead_scoring.yml"
    report_output_path: str = "Lead_Intelligence_Report.xlsx"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "lead_qualification"
    postgres_user: str = "lead_user"
    postgres_password: str = Field(default="lead_password", repr=False)

    database_pool_size: int = 5
    database_max_overflow: int = 10

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = Field(default="", repr=False)
    smtp_sender: str = ""
    smtp_use_tls: bool = True
    report_email_recipients: str = ""

    telegram_bot_token: str = Field(default="", repr=False)
    telegram_chat_id: str = ""
    telegram_chat_ids: str = ""

    report_delivery_retry_attempts: int = 3
    report_delivery_retry_backoff_seconds: float = 2
    report_scheduler_enabled: bool = False
    report_scheduler_timezone: str = "Asia/Kolkata"
    daily_report_time: str = "09:00"
    weekly_report_day: str = "mon"
    monthly_report_day: int = 1

    @cached_property
    def database_url(self) -> str:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    @cached_property
    def sync_database_url(self) -> str:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)


settings = Settings()
