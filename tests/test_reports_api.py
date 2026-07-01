from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.api.v1.reports import EXCEL_MEDIA_TYPE, get_excel_report_generator
from app.main import create_app


class FakeReportGenerator:
    def __init__(self, output_path: Path, *, should_fail: bool = False) -> None:
        self.output_path = output_path
        self.should_fail = should_fail

    def generate_report(self) -> Path:
        if self.should_fail:
            raise RuntimeError("report failed")
        workbook = Workbook()
        workbook.active.title = "Executive Summary"
        workbook.save(self.output_path)
        return self.output_path


@pytest.fixture
def report_path(tmp_path: Path) -> Path:
    return tmp_path / "Lead_Intelligence_Report.xlsx"


def test_download_lead_intelligence_report(report_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_excel_report_generator] = lambda: FakeReportGenerator(report_path)
    client = TestClient(app)

    response = client.get("/reports/lead-intelligence.xlsx")

    assert response.status_code == 200
    assert response.headers["content-type"] == EXCEL_MEDIA_TYPE
    assert "Lead_Intelligence_Report.xlsx" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK")


def test_download_lead_intelligence_report_handles_generation_errors(report_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_excel_report_generator] = lambda: FakeReportGenerator(
        report_path,
        should_fail=True,
    )
    client = TestClient(app)

    response = client.get("/reports/lead-intelligence.xlsx")

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to generate lead intelligence report"
