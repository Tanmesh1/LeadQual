from pydantic import BaseModel, ConfigDict


class HealthCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    environment: str
    database: str
