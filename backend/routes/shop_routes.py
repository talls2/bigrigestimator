"""
Shop routes: manage shop configuration and reference data.
GET /info - shop info
PUT /info - update shop info
GET /rates - shop rates
GET /templates - letter templates
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.shop_service import ShopService

router = APIRouter(prefix="/api/shop", tags=["shop"])
service = ShopService()


class ShopInfoIn(BaseModel):
    shop_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    license_number: Optional[str] = None
    notes: Optional[str] = None


@router.get("/info")
def get_shop_info():
    """Get shop information."""
    try:
        info = service.get_info()
        if not info:
            raise HTTPException(status_code=404, detail="Shop information not configured")
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/info")
def update_shop_info(data: ShopInfoIn):
    """Update shop information."""
    try:
        service.update_info(data.dict(exclude_unset=True))
        return {"message": "Shop information updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rates")
def get_shop_rates():
    """Get shop rates (labor rates, etc.)."""
    try:
        rates = service.get_rates()
        return rates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
def get_letter_templates():
    """Get letter templates for correspondence."""
    try:
        templates = service.get_templates()
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
