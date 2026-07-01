from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.reports.excel_report import DEFAULT_OUTPUT_PATH, ExcelReportGenerator

router = APIRouter(prefix="/reports", tags=["reports"])

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
REPORT_FILENAME = "Lead_Intelligence_Report.xlsx"


def get_excel_report_generator() -> ExcelReportGenerator:
    output_path = Path(".runtime") / "reports" / DEFAULT_OUTPUT_PATH.name
    return ExcelReportGenerator(output_path=output_path)


@router.get("/lead-intelligence.xlsx", response_class=FileResponse)
def download_lead_intelligence_report(
    generator: Annotated[ExcelReportGenerator, Depends(get_excel_report_generator)],
) -> FileResponse:
    try:
        report_path = generator.generate_report()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate lead intelligence report",
        ) from exc

    return FileResponse(
        path=report_path,
        filename=REPORT_FILENAME,
        media_type=EXCEL_MEDIA_TYPE,
    )
