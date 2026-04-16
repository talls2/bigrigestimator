"""
Report routes: generate shop reports and analytics.
GET /production-summary (?start_date=, ?end_date=)
GET /ar-aging
GET /employee-productivity
GET /parts-summary
GET /cycle-time
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])
service = ReportService()


@router.get("/production-summary")
def get_production_summary(start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None)):
    """Get production summary report with optional date range filtering."""
    try:
        summary = service.production_summary(start_date=start_date, end_date=end_date)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ar-aging")
def get_ar_aging():
    """Get accounts receivable aging report."""
    try:
        aging = service.ar_aging()
        return aging
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employee-productivity")
def get_employee_productivity():
    """Get employee productivity report."""
    try:
        productivity = service.employee_productivity()
        return productivity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parts-summary")
def get_parts_summary():
    """Get parts usage and vendor summary report."""
    try:
        parts = service.parts_summary()
        return parts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cycle-time")
def get_cycle_time():
    """Get cycle time analysis report."""
    try:
        cycle = service.cycle_time()
        return cycle
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
