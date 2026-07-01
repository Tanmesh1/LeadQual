import asyncio

from app.core.logging import configure_logging
from app.delivery.services.delivery_agent import ReportDeliveryAgent


async def main() -> None:
    configure_logging()
    await ReportDeliveryAgent().deliver_report()


if __name__ == "__main__":
    asyncio.run(main())
