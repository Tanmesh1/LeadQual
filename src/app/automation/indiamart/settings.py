from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IndiaMartAutomationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    indiamart_mobile_number: str | None = Field(default=None, repr=False)
    indiamart_username: str | None = Field(default=None, repr=False)
    indiamart_password: str | None = Field(default=None, repr=False)
    indiamart_headless: bool = True
    indiamart_slow_mo_ms: int = Field(default=0, ge=0)
    indiamart_timeout_ms: int = Field(default=30_000, ge=1_000)
    indiamart_manual_login_timeout_seconds: int = Field(default=120, ge=10)
    indiamart_lead_list_wait_seconds: int = Field(default=20, ge=1)
    indiamart_max_pages: int = Field(default=10, ge=1)
    indiamart_batch_size: int = Field(default=25, ge=1, le=100)
    indiamart_open_lead_details: bool = False
    indiamart_api_base_url: str = "http://localhost:8000/api/v1"
    indiamart_session_state_path: Path = Path(".runtime/indiamart/storage_state.json")
    indiamart_diagnostics_path: Path = Path(".runtime/indiamart/diagnostics")
    indiamart_selectors_path: Path = Path(
        "src/app/automation/indiamart/selectors/buy_leads.json"
    )
    indiamart_retry_attempts: int = Field(default=3, ge=1)
    indiamart_retry_backoff_seconds: float = Field(default=1.0, ge=0)


settings = IndiaMartAutomationSettings()
