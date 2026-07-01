from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryResult:
    recipient: str
    success: bool
    attempts: int
    error_message: str | None = None

    @property
    def status(self) -> str:
        return "sent" if self.success else "failed"
