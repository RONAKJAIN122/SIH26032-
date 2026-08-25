"""
Farmer-facing API endpoints for the SmartMandi Farmer Portal.
Handles phone-based login lookup, self-registration, and farmer booking queries.
"""
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/farmers", tags=["Farmer Portal"])


# ---------------------------------------------------------------------------
# 1. Phone-based login lookup (KYC check)
# ---------------------------------------------------------------------------
@router.get("/by-phone/{phone}", response_model=schemas.FarmerResponse)
def get_farmer_by_phone(phone: str, db: Session = Depends(get_db)):
    """
    Look up a farmer by their 10-digit phone number.
    Used as the primary login mechanism in the Farmer Portal.
    Returns 404 if not found (frontend then offers registration flow).
    """
    # Normalize: strip spaces/dashes, keep digits only
    clean_phone = "".join(filter(str.isdigit, phone))
    farmer = db.query(models.Farmer).filter(
        models.Farmer.phone_number == clean_phone
    ).first()
    if not farmer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No farmer registered with phone {clean_phone}. Please register first."
        )
    return farmer


# ---------------------------------------------------------------------------
# 2. Self-registration for new farmers
# ---------------------------------------------------------------------------
@router.post("/register", response_model=schemas.FarmerResponse, status_code=status.HTTP_201_CREATED)
def register_farmer(farmer_data: schemas.FarmerCreate, db: Session = Depends(get_db)):
    """
    Register a new farmer via the self-service portal.
    Phone number must be unique.
    """
    existing = db.query(models.Farmer).filter(
        models.Farmer.phone_number == farmer_data.phone_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A farmer with this phone number is already registered. Please login instead."
        )
    new_farmer = models.Farmer(**farmer_data.model_dump())
    db.add(new_farmer)
    db.commit()
    db.refresh(new_farmer)
    return new_farmer


# ---------------------------------------------------------------------------
# 3. Get all bookings for a specific farmer
# ---------------------------------------------------------------------------
@router.get("/{farmer_id}/bookings", response_model=List[schemas.FarmerBookingDetail])
def get_farmer_bookings(
    farmer_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Return all bookings for a farmer, newest first.
    Enriched with center name, queue position (farmers ahead), and ETA.
    """
    farmer = db.query(models.Farmer).filter(models.Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found.")

    bookings = (
        db.query(models.Booking)
        .filter(models.Booking.farmer_id == farmer_id)
        .order_by(models.Booking.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    active_statuses = [
        models.BookingStatus.CONFIRMED,
        models.BookingStatus.CHECKED_IN,
        models.BookingStatus.WEIGHING,
    ]

    for b in bookings:
        # Count active farmers ahead in queue at the same center & date
        farmers_ahead = db.query(models.Booking).filter(
            models.Booking.center_id == b.center_id,
            models.Booking.booking_date == b.booking_date,
            models.Booking.status.in_(active_statuses),
            models.Booking.queue_number < b.queue_number
        ).count()

        result.append(schemas.FarmerBookingDetail(
            booking_id=b.id,
            booking_reference=b.booking_reference,
            center_id=b.center_id,
            center_name=b.center.name if b.center else "Unknown",
            center_district=b.center.district if b.center else "",
            queue_number=b.queue_number,
            booking_date=str(b.booking_date),
            crop_type=b.crop_type,
            estimated_quantity_quintals=b.estimated_quantity_quintals,
            status=b.status,
            estimated_arrival_time=(
                b.estimated_arrival_time.strftime("%I:%M %p")
                if b.estimated_arrival_time else None
            ),
            farmers_ahead=farmers_ahead,
            created_at=str(b.created_at),
        ))

    return result


# ---------------------------------------------------------------------------
# 4. Center availability for a given date (for date picker validation)
# ---------------------------------------------------------------------------
@router.get("/centers/{center_id}/availability")
def get_center_availability(
    center_id: int,
    booking_date: date = Query(..., description="Date to check availability for"),
    db: Session = Depends(get_db)
):
    """
    Returns remaining quintal capacity and slot count for a center on a given date.
    Used by the farmer portal to show live availability before booking.
    """
    center = db.query(models.Center).filter(models.Center.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found.")

    booked_qty = db.query(func.coalesce(func.sum(models.Booking.estimated_quantity_quintals), 0)).filter(
        models.Booking.center_id == center_id,
        models.Booking.booking_date == booking_date,
        models.Booking.status != models.BookingStatus.CANCELLED,
    ).scalar() or 0.0

    active_bookings_count = db.query(models.Booking).filter(
        models.Booking.center_id == center_id,
        models.Booking.booking_date == booking_date,
        models.Booking.status != models.BookingStatus.CANCELLED,
    ).count()

    remaining_qty = max(0.0, center.daily_capacity_quintals - booked_qty)
    utilization_pct = round((booked_qty / center.daily_capacity_quintals) * 100, 1) if center.daily_capacity_quintals > 0 else 0

    return {
        "center_id": center.id,
        "center_name": center.name,
        "center_district": center.district,
        "date": str(booking_date),
        "daily_capacity_quintals": center.daily_capacity_quintals,
        "booked_quintals": round(booked_qty, 1),
        "remaining_quintals": round(remaining_qty, 1),
        "total_bookings_today": active_bookings_count,
        "utilization_percent": utilization_pct,
        "is_available": remaining_qty > 0,
    }
