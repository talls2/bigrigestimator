"""
Repair order routes: manage repair orders.
GET / - list (?status=, ?search=)
GET /{id} - get full RO with lines, payments, timecards, production
POST / - create
PUT /{id} - update
POST /{id}/lines - add line
POST /{id}/payments - add payment
PATCH /{id}/status - update status only
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from services.repair_order_service import RepairOrderService

router = APIRouter(prefix="/api/repair-orders", tags=["repair-orders"])
service = RepairOrderService()


class RepairOrderIn(BaseModel):
    customer_id: int
    vehicle_id: Optional[int] = None
    insurance_company_id: Optional[int] = None
    estimator_id: Optional[int] = None
    claim_number: Optional[str] = None
    policy_number: Optional[str] = None
    deductible: float = 0
    status: str = "open"
    priority: str = "normal"
    loss_date: Optional[str] = None
    notes: Optional[str] = None


class RepairOrderLineIn(BaseModel):
    line_type: str = "labor"
    operation: Optional[str] = None
    description: str = ""
    part_number: Optional[str] = None
    part_type: Optional[str] = None
    quantity: float = 1
    labor_hours: float = 0
    labor_rate: float = 0
    paint_hours: float = 0
    paint_rate: float = 0
    part_price: float = 0
    part_cost: float = 0
    is_supplement: int = 0
    vendor_id: Optional[int] = None
    assigned_tech_id: Optional[int] = None
    notes: Optional[str] = None


class PaymentIn(BaseModel):
    amount: float
    payment_date: Optional[str] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    payer_type: Optional[str] = None
    payer_name: Optional[str] = None
    notes: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


@router.get("")
def list_repair_orders(status: Optional[str] = Query(None), search: Optional[str] = Query(None)):
    """List repair orders with optional status and search filtering."""
    try:
        ros = service.list_ros(status=status, search=search)
        return ros
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ro_id}")
def get_repair_order(ro_id: int):
    """Get a complete repair order with all details, lines, payments, and timecards."""
    try:
        ro = service.get_ro(ro_id)
        if not ro:
            raise HTTPException(status_code=404, detail=f"Repair order {ro_id} not found")
        return ro
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_repair_order(data: RepairOrderIn):
    """Create a new repair order."""
    try:
        ro_id = service.create_ro(data.dict())
        return {"id": ro_id, "message": "Repair order created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{ro_id}")
def update_repair_order(ro_id: int, data: RepairOrderIn):
    """Update an existing repair order."""
    try:
        service.update_ro(ro_id, data.dict(exclude_unset=True))
        return {"id": ro_id, "message": "Repair order updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ro_id}/lines")
def add_repair_order_line(ro_id: int, data: RepairOrderLineIn):
    """Add a line item to a repair order."""
    try:
        line_id = service.add_line(ro_id, data.dict())
        return {"id": line_id, "message": "Line item added successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ro_id}/payments")
def add_repair_order_payment(ro_id: int, data: PaymentIn):
    """Add a payment to a repair order."""
    try:
        payment_id = service.add_payment(ro_id, data.dict())
        return {"id": payment_id, "message": "Payment added successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ro_id}/status")
def update_repair_order_status(ro_id: int, data: StatusUpdate):
    """Update the status of a repair order."""
    try:
        service.update_status(ro_id, data.status)
        return {"id": ro_id, "message": "Status updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
