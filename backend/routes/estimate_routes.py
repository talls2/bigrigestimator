"""
Estimate routes: manage estimates.
GET / - list (?status=, ?search=)
GET /{id} - get full estimate with lines
POST / - create
PUT /{id} - update
POST /{id}/lines - add line item
DELETE /{id}/lines/{line_id} - delete line
POST /{id}/convert-to-ro - convert estimate to repair order
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from services.estimate_service import EstimateService

router = APIRouter(prefix="/api/estimates", tags=["estimates"])
service = EstimateService()


class EstimateIn(BaseModel):
    customer_id: int
    vehicle_id: Optional[int] = None
    insurance_company_id: Optional[int] = None
    insurance_agent_id: Optional[int] = None
    estimator_id: Optional[int] = None
    claim_number: Optional[str] = None
    policy_number: Optional[str] = None
    deductible: float = 0
    status: str = "pending"
    loss_date: Optional[str] = None
    point_of_impact: Optional[str] = None
    damage_description: Optional[str] = None
    tax_exempt: Optional[int] = None
    notes: Optional[str] = None


class EstimateLineIn(BaseModel):
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
    supplement_number: int = 0
    taxable: Optional[int] = None
    notes: Optional[str] = None


@router.get("")
def list_estimates(status: Optional[str] = Query(None), search: Optional[str] = Query(None)):
    """List estimates with optional status and search filtering."""
    try:
        estimates = service.list_estimates(status=status, search=search)
        return estimates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{estimate_id}")
def get_estimate(estimate_id: int):
    """Get a complete estimate with all details and line items."""
    try:
        estimate = service.get_estimate(estimate_id)
        if not estimate:
            raise HTTPException(status_code=404, detail=f"Estimate {estimate_id} not found")
        return estimate
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_estimate(data: EstimateIn):
    """Create a new estimate."""
    try:
        estimate_id = service.create_estimate(data.dict())
        return {"id": estimate_id, "message": "Estimate created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{estimate_id}")
def update_estimate(estimate_id: int, data: EstimateIn):
    """Update an existing estimate."""
    try:
        service.update_estimate(estimate_id, data.dict(exclude_unset=True))
        return {"id": estimate_id, "message": "Estimate updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{estimate_id}/lines")
def add_estimate_line(estimate_id: int, data: EstimateLineIn):
    """Add a line item to an estimate."""
    try:
        line_id = service.add_line(estimate_id, data.dict())
        return {"id": line_id, "message": "Line item added successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{estimate_id}/lines/{line_id}")
def delete_estimate_line(estimate_id: int, line_id: int):
    """Delete a line item from an estimate."""
    try:
        service.delete_line(estimate_id, line_id)
        return {"message": "Line item deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{estimate_id}/convert-to-ro")
def convert_estimate_to_ro(estimate_id: int):
    """Convert an estimate to a repair order."""
    try:
        result = service.convert_to_ro(estimate_id)
        if isinstance(result, dict):
            return result
        # Backward compat: if service returns just an ID
        return {"id": result, "message": "Estimate converted to repair order successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
