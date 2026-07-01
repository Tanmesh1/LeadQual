from fastapi.testclient import TestClient

from app.dependencies.database import get_database_session
from app.main import create_app


class RefusedDatabaseSession:
    async def execute(self, statement: object) -> None:
        raise ConnectionRefusedError("database refused the connection")


async def get_refused_database_session():
    yield RefusedDatabaseSession()


def test_health_reports_database_unavailable_when_connection_is_refused() -> None:
    app = create_app()
    app.dependency_overrides[get_database_session] = get_refused_database_session
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert response.json()["database"] == "unavailable"
