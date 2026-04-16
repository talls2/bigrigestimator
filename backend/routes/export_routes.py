"""
Export & PDF routes.
GET /api/exports/estimate/{id}/pdf - estimate PDF
GET /api/exports/ro/{id}/invoice-pdf - invoice PDF
GET /api/exports/ro/{id}/work-order-pdf - work order PDF
GET /api/exports/quickbooks - QuickBooks IIF export
GET /api/exports/xml - Generic XML export
GET /api/exports/mitchell-connect - Mitchell Connect XML export
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from services.pdf_service import (
    generate_estimate_pdf, generate_invoice_pdf, generate_work_order_pdf
)
from services.export_service import ExportService
from config.database import get_db, row_to_dict, rows_to_list

router = APIRouter(prefix="/api/exports", tags=["exports"])
export_svc = ExportService()


def _get_shop():
    with get_db() as db:
        row = db.execute("SELECT * FROM body_shop LIMIT 1").fetchone()
    return row_to_dict(row) if row else None


@router.get("/estimate/{estimate_id}/pdf")
def estimate_pdf(estimate_id: int):
    """Generate and download an estimate as PDF."""
    with get_db() as db:
        est = db.execute("""
            SELECT e.*, c.first_name AS customer_first, c.last_name AS customer_last,
                   c.company_name, v.year, v.make, v.model, v.vin, v.color,
                   ic.company_name AS insurance_name
            FROM estimates e
            LEFT JOIN customers c ON e.customer_id = c.id
            LEFT JOIN vehicles v ON e.vehicle_id = v.id
            LEFT JOIN insurance_companies ic ON e.insurance_company_id = ic.id
            WHERE e.id = ?
        """, (estimate_id,)).fetchone()
        if not est:
            raise HTTPException(status_code=404, detail="Estimate not found")
        est = row_to_dict(est)

        lines = rows_to_list(db.execute(
            "SELECT * FROM estimate_lines WHERE estimate_id = ? ORDER BY line_number",
            (estimate_id,)
        ).fetchall())

    shop = _get_shop()
    buf = generate_estimate_pdf(est, lines, shop)
    filename = f"Estimate_{est.get('estimate_number', estimate_id)}.pdf"

    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/ro/{ro_id}/invoice-pdf")
def invoice_pdf(ro_id: int):
    """Generate and download an invoice PDF for a repair order."""
    with get_db() as db:
        ro = db.execute("""
            SELECT ro.*, c.first_name AS customer_first, c.last_name AS customer_last,
                   c.company_name, v.year, v.make, v.model, v.vin, v.color, v.mileage,
                   ic.company_name AS insurance_name
            FROM repair_orders ro
            LEFT JOIN customers c ON ro.customer_id = c.id
            LEFT JOIN vehicles v ON ro.vehicle_id = v.id
            LEFT JOIN insurance_companies ic ON ro.insurance_company_id = ic.id
            WHERE ro.id = ?
        """, (ro_id,)).fetchone()
        if not ro:
            raise HTTPException(status_code=404, detail="Repair order not found")
        ro = row_to_dict(ro)

        lines = rows_to_list(db.execute(
            "SELECT * FROM ro_lines WHERE ro_id = ? ORDER BY line_number",
            (ro_id,)
        ).fetchall())

        payments = rows_to_list(db.execute(
            "SELECT * FROM payments WHERE ro_id = ? ORDER BY payment_date",
            (ro_id,)
        ).fetchall())

    shop = _get_shop()
    buf = generate_invoice_pdf(ro, lines, payments, shop)
    filename = f"Invoice_{ro.get('ro_number', ro_id)}.pdf"

    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/ro/{ro_id}/work-order-pdf")
def work_order_pdf(ro_id: int):
    """Generate and download a work order PDF for the shop floor."""
    with get_db() as db:
        ro = db.execute("""
            SELECT ro.*, c.first_name AS customer_first, c.last_name AS customer_last,
                   c.company_name, v.year, v.make, v.model, v.vin, v.color,
                   t.first_name AS tech_first, t.last_name AS tech_last,
                   p.first_name AS painter_first, p.last_name AS painter_last
            FROM repair_orders ro
            LEFT JOIN customers c ON ro.customer_id = c.id
            LEFT JOIN vehicles v ON ro.vehicle_id = v.id
            LEFT JOIN employees t ON ro.technician_id = t.id
            LEFT JOIN employees p ON ro.painter_id = p.id
            WHERE ro.id = ?
        """, (ro_id,)).fetchone()
        if not ro:
            raise HTTPException(status_code=404, detail="Repair order not found")
        ro = row_to_dict(ro)

        lines = rows_to_list(db.execute(
            "SELECT * FROM ro_lines WHERE ro_id = ? ORDER BY line_number",
            (ro_id,)
        ).fetchall())

    shop = _get_shop()
    buf = generate_work_order_pdf(ro, lines, shop)
    filename = f"WorkOrder_{ro.get('ro_number', ro_id)}.pdf"

    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/quickbooks")
def quickbooks_export(date_from: Optional[str] = Query(None),
                      date_to: Optional[str] = Query(None)):
    """Export data as QuickBooks IIF file."""
    try:
        content = export_svc.export_quickbooks_iif(date_from, date_to)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=shop_manager_export.iif"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xml")
def xml_export(date_from: Optional[str] = Query(None),
               date_to: Optional[str] = Query(None)):
    """Export data as generic XML."""
    try:
        content = export_svc.export_xml(date_from, date_to)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/xml",
            headers={"Content-Disposition": "attachment; filename=shop_manager_export.xml"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mitchell-connect")
def mitchell_connect_export(date_from: Optional[str] = Query(None),
                            date_to: Optional[str] = Query(None)):
    """Export estimates as Mitchell Connect compatible XML."""
    try:
        content = export_svc.export_mitchell_connect_xml(date_from, date_to)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/xml",
            headers={"Content-Disposition": "attachment; filename=mitchell_connect_export.xml"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import io
