import random
import asyncio
from datetime import date, datetime, timedelta, time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/api",
    tags=["Queue & Booking Operations"]
)

# Standard Mandi operational start time: 08:00 AM
MANDI_START_HOUR = 8
MANDI_START_MINUTE = 0
DEFAULT_PROCESSING_TIME_MINS = 15.0


def calculate_initial_eta(booking_date: date, queue_number: int, avg_duration_mins: float = 15.0) -> datetime:
    """Calculate the estimated arrival time for a given queue position on booking date."""
    base_start = datetime.combine(booking_date, time(MANDI_START_HOUR, MANDI_START_MINUTE))
    offset_minutes = (queue_number - 1) * avg_duration_mins
    return base_start + timedelta(minutes=offset_minutes)


def get_center_avg_processing_time(db: Session, center_id: int, target_date: date) -> float:
    """Calculate the real-time average processing duration (in mins) of completed bookings today."""
    completed_bookings = db.query(models.Booking).filter(
        models.Booking.center_id == center_id,
        models.Booking.booking_date == target_date,
        models.Booking.status == models.BookingStatus.COMPLETED,
        models.Booking.processing_duration_minutes.isnot(None)
    ).all()

    if not completed_bookings:
        return DEFAULT_PROCESSING_TIME_MINS

    durations = [b.processing_duration_minutes for b in completed_bookings if b.processing_duration_minutes > 0]
    if not durations:
        return DEFAULT_PROCESSING_TIME_MINS

    return round(sum(durations) / len(durations), 1)


# -------------------------------------------------------------------
# 1. Slot Booking Endpoint (POST /api/bookings)
# -------------------------------------------------------------------
@router.post("/bookings", response_model=schemas.SlotBookingResponse, status_code=status.HTTP_201_CREATED)
def book_procurement_slot(
    request: schemas.SlotBookingRequest,
    db: Session = Depends(get_db)
):
    """
    Core slot booking algorithm:
    1. Validates farmer & center existence.
    2. Checks daily capacity against confirmed bookings with DB transaction isolation.
    3. If capacity available -> assigns dynamic queue number & calculates ETA.
    4. If capacity exceeded -> rejects and calculates next available date.
    """
    # 1. Validate Farmer
    farmer = db.query(models.Farmer).filter(models.Farmer.id == request.farmer_id).first()
    if not farmer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farmer with ID {request.farmer_id} not found."
        )

    # 2. Validate Center & Lock for Capacity Check
    try:
        # with_for_update() provides database row-level locking on PostgreSQL
        center = db.query(models.Center).filter(models.Center.id == request.center_id).with_for_update().first()
    except Exception:
        # Fallback for SQLite in local test mode
        center = db.query(models.Center).filter(models.Center.id == request.center_id).first()

    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Procurement Center with ID {request.center_id} not found."
        )

    if not center.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Procurement Center '{center.name}' is currently inactive."
        )

    # 3. Check Capacity on Requested Date
    active_statuses = [
        models.BookingStatus.CONFIRMED,
        models.BookingStatus.CHECKED_IN,
        models.BookingStatus.WEIGHING,
        models.BookingStatus.COMPLETED,
        models.BookingStatus.PENDING,
    ]

    total_booked_qty = db.query(
        func.coalesce(func.sum(models.Booking.estimated_quantity_quintals), 0.0)
    ).filter(
        models.Booking.center_id == request.center_id,
        models.Booking.booking_date == request.requested_date,
        models.Booking.status.in_(active_statuses)
    ).scalar()

    available_capacity = center.daily_capacity_quintals - total_booked_qty

    # 4. If Capacity Exceeded -> Find Next Available Date & Reject
    if (total_booked_qty + request.estimated_quantity_quintals) > center.daily_capacity_quintals:
        # Scan next 7 days for an available slot
        suggested_date = None
        for day_offset in range(1, 8):
            next_date = request.requested_date + timedelta(days=day_offset)
            next_day_booked = db.query(
                func.coalesce(func.sum(models.Booking.estimated_quantity_quintals), 0.0)
            ).filter(
                models.Booking.center_id == request.center_id,
                models.Booking.booking_date == next_date,
                models.Booking.status.in_(active_statuses)
            ).scalar()

            if (next_day_booked + request.estimated_quantity_quintals) <= center.daily_capacity_quintals:
                suggested_date = next_date
                break

        suggestion_text = f" Next available date with sufficient capacity is {suggested_date}." if suggested_date else " No available slots in the next 7 days."

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CAPACITY_EXCEEDED",
                "message": f"Center daily procurement capacity ({center.daily_capacity_quintals} Q) exceeded for {request.requested_date}. Remaining capacity: {available_capacity:.1f} Q.{suggestion_text}",
                "requested_date": str(request.requested_date),
                "requested_quantity_quintals": request.estimated_quantity_quintals,
                "remaining_capacity_quintals": max(0.0, available_capacity),
                "suggested_available_date": str(suggested_date) if suggested_date else None
            }
        )

    # 5. Capacity is Available -> Assign Next Dynamic Queue Number
    max_queue = db.query(
        func.coalesce(func.max(models.Booking.queue_number), 0)
    ).filter(
        models.Booking.center_id == request.center_id,
        models.Booking.booking_date == request.requested_date
    ).scalar()

    dynamic_queue_number = max_queue + 1

    # 6. Calculate Initial ETA
    avg_duration = get_center_avg_processing_time(db, center.id, request.requested_date)
    estimated_arrival = calculate_initial_eta(request.requested_date, dynamic_queue_number, avg_duration)

    # 7. Generate Reference Code
    rand_suffix = random.randint(100, 999)
    clean_code = center.code.replace("MANDI-", "").replace("-", "")
    booking_ref = f"BK-{request.requested_date.strftime('%y%m%d')}-{clean_code}-{dynamic_queue_number:03d}-{rand_suffix}"

    # 8. Create Booking Record
    new_booking = models.Booking(
        booking_reference=booking_ref,
        center_id=request.center_id,
        farmer_id=request.farmer_id,
        booking_date=request.requested_date,
        queue_number=dynamic_queue_number,
        crop_type=request.crop_type,
        estimated_quantity_quintals=request.estimated_quantity_quintals,
        status=models.BookingStatus.CONFIRMED,
        estimated_arrival_time=estimated_arrival,
        created_at=datetime.utcnow()
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return schemas.SlotBookingResponse(
        booking_id=new_booking.id,
        booking_reference=new_booking.booking_reference,
        queue_number=new_booking.queue_number,
        status=new_booking.status,
        booking_date=new_booking.booking_date,
        crop_type=new_booking.crop_type,
        estimated_quantity_quintals=new_booking.estimated_quantity_quintals,
        estimated_arrival_time=new_booking.estimated_arrival_time,
        estimated_arrival_time_formatted=new_booking.estimated_arrival_time.strftime("%I:%M %p, %d %b %Y"),
        center_name=center.name,
        center_district=center.district,
        farmer_name=farmer.name,
        farmer_phone=farmer.phone_number,
        message=f"Slot confirmed! Token #{dynamic_queue_number} assigned. Estimated arrival time: {new_booking.estimated_arrival_time.strftime('%I:%M %p')}."
    )


# -------------------------------------------------------------------
# 2. Dynamic Queue & Status Update (PATCH /api/bookings/{booking_id}/status)
# -------------------------------------------------------------------
@router.patch("/bookings/{booking_id}/status", response_model=schemas.StatusUpdateResponse)
async def update_booking_status(
    booking_id: int,
    status_update: schemas.StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates booking status:
    PENDING -> CONFIRMED -> CHECKED_IN -> WEIGHING -> COMPLETED / CANCELLED.
    Automatically recalculates dynamic ETAs for all remaining farmers in queue
    based on the real-time average processing duration of completed bookings today.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found."
        )

    old_status = booking.status
    new_status = status_update.status
    now = datetime.utcnow()

    # Track lifecycle timestamps
    if new_status == models.BookingStatus.CHECKED_IN and not booking.checked_in_at:
        booking.checked_in_at = now
    elif new_status == models.BookingStatus.WEIGHING and not booking.weighing_started_at:
        booking.weighing_started_at = now
    elif new_status == models.BookingStatus.COMPLETED:
        booking.completed_at = now
        # Calculate actual duration spent
        start_time = booking.weighing_started_at or booking.checked_in_at or booking.created_at
        if start_time:
            duration = (now - start_time).total_seconds() / 60.0
            # If duration is 0 (immediate test click), assign reasonable standard duration ~12.5 mins
            booking.processing_duration_minutes = round(max(duration, 12.5), 1)

    booking.status = new_status
    db.commit()
    db.refresh(booking)

    # Recalculate Dynamic Average Duration for this Center & Date
    avg_processing_time = get_center_avg_processing_time(db, booking.center_id, booking.booking_date)

    # Recalculate dynamic ETAs for all active bookings remaining in the queue
    active_remaining = db.query(models.Booking).filter(
        models.Booking.center_id == booking.center_id,
        models.Booking.booking_date == booking.booking_date,
        models.Booking.status.in_([
            models.BookingStatus.CONFIRMED,
            models.BookingStatus.CHECKED_IN,
            models.BookingStatus.WEIGHING
        ])
    ).order_by(models.Booking.queue_number.asc()).all()

    current_time_cursor = datetime.utcnow()
    for index, active_b in enumerate(active_remaining):
        # Update arrival/process ETA dynamically
        active_b.estimated_arrival_time = current_time_cursor + timedelta(minutes=index * avg_processing_time)

    db.commit()

    # -----------------------------------------------------------
    # Broadcast live queue update to all WebSocket dashboard clients
    # -----------------------------------------------------------
    try:
        from routers.ws import manager, build_queue_broadcast_payload
        payload = build_queue_broadcast_payload(db, booking.center_id, booking.booking_date)
        if payload:
            asyncio.create_task(manager.broadcast(payload))
    except Exception as ws_err:
        print(f"[WS Broadcast] Non-critical error: {ws_err}")

    # -----------------------------------------------------------
    # Mock SMS/WhatsApp push notification on COMPLETED status
    # (In production: fire real Twilio message to farmer)
    # -----------------------------------------------------------
    if new_status == models.BookingStatus.COMPLETED and booking.farmer:
        farmer_name = booking.farmer.name
        farmer_phone = booking.farmer.phone_number
        msb_per_q = 2275.0
        payout = round(booking.estimated_quantity_quintals * msb_per_q, 2)
        sms_text = (
            f"[SmartMandi] Namaste {farmer_name}! "
            f"Your {booking.crop_type} ({booking.estimated_quantity_quintals} Q) has been weighed. "
            f"Estimated payout: Rs {payout:,.2f} at MSP. "
            f"Ref: {booking.booking_reference}"
        )
        # In production, replace with actual Twilio send:
        # client.messages.create(body=sms_text, from_=TWILIO_NUMBER, to=f"+91{farmer_phone}")
        print(f"[Mock SMS] To +91{farmer_phone}: {sms_text}")

    return schemas.StatusUpdateResponse(
        booking_id=booking.id,
        booking_reference=booking.booking_reference,
        old_status=old_status,
        new_status=new_status,
        processing_duration_minutes=booking.processing_duration_minutes,
        average_processing_time_minutes=avg_processing_time,
        recalculated_queue_count=len(active_remaining),
        message=f"Booking status updated from {old_status.value} to {new_status.value}. Dynamic ETAs recalculated for {len(active_remaining)} farmers at {avg_processing_time:.1f} mins/turn."
    )


# -------------------------------------------------------------------
# 3. Live Queue for Center (GET /api/centers/{center_id}/live-queue)
# -------------------------------------------------------------------
@router.get("/centers/{center_id}/live-queue", response_model=schemas.CenterLiveQueueResponse)
def get_center_live_queue(
    center_id: int,
    target_date: Optional[date] = Query(None, description="Date to inspect (defaults to today)"),
    db: Session = Depends(get_db)
):
    """
    Returns all active bookings for a center sorted by queue number,
    including live queue positions and real-time ETAs.
    """
    center = db.query(models.Center).filter(models.Center.id == center_id).first()
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Procurement Center with ID {center_id} not found."
        )

    check_date = target_date or date.today()

    # Query all bookings for this center and date
    bookings = db.query(models.Booking).filter(
        models.Booking.center_id == center_id,
        models.Booking.booking_date == check_date
    ).order_by(models.Booking.queue_number.asc()).all()

    avg_processing_time = get_center_avg_processing_time(db, center_id, check_date)

    active_statuses = [
        models.BookingStatus.CONFIRMED,
        models.BookingStatus.CHECKED_IN,
        models.BookingStatus.WEIGHING
    ]

    active_bookings = [b for b in bookings if b.status in active_statuses]
    completed_count = sum(1 for b in bookings if b.status == models.BookingStatus.COMPLETED)
    booked_qty = sum(b.estimated_quantity_quintals for b in bookings if b.status != models.BookingStatus.CANCELLED)

    # Build queue list with farmers_ahead & dynamic ETAs
    queue_items = []
    for idx, b in enumerate(active_bookings):
        farmers_ahead = idx
        eta_formatted = b.estimated_arrival_time.strftime("%I:%M %p") if b.estimated_arrival_time else f"~{int(farmers_ahead * avg_processing_time)} mins"

        farmer_name = b.farmer.name if b.farmer else f"Farmer #{b.farmer_id}"
        farmer_phone = b.farmer.phone_number if b.farmer else "N/A"

        queue_items.append(
            schemas.LiveQueueItem(
                booking_id=b.id,
                booking_reference=b.booking_reference,
                queue_number=b.queue_number,
                status=b.status,
                farmer_id=b.farmer_id,
                farmer_name=farmer_name,
                farmer_phone=farmer_phone,
                crop_type=b.crop_type,
                estimated_quantity_quintals=b.estimated_quantity_quintals,
                dynamic_eta=eta_formatted,
                farmers_ahead=farmers_ahead
            )
        )

    return schemas.CenterLiveQueueResponse(
        center_id=center.id,
        center_name=center.name,
        date=check_date,
        daily_capacity_quintals=center.daily_capacity_quintals,
        booked_capacity_quintals=booked_qty,
        active_in_queue_count=len(active_bookings),
        completed_today_count=completed_count,
        average_processing_time_minutes=avg_processing_time,
        queue=queue_items
    )


# -------------------------------------------------------------------
# 4. Farmer Live Booking & Dynamic ETA (GET /api/farmers/{phone_number}/active-booking)
# -------------------------------------------------------------------
@router.get("/farmers/{phone_number}/active-booking", response_model=schemas.ActiveFarmerBookingResponse)
def get_farmer_active_booking(
    phone_number: str,
    db: Session = Depends(get_db)
):
    """
    Returns the live queue position and dynamic ETA for a farmer by mobile number.
    """
    farmer = db.query(models.Farmer).filter(models.Farmer.phone_number == phone_number).first()
    if not farmer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farmer with phone number '{phone_number}' not found."
        )

    # Find the most recent active booking for this farmer
    active_statuses = [
        models.BookingStatus.CONFIRMED,
        models.BookingStatus.CHECKED_IN,
        models.BookingStatus.WEIGHING,
        models.BookingStatus.PENDING
    ]

    booking = db.query(models.Booking).filter(
        models.Booking.farmer_id == farmer.id,
        models.Booking.status.in_(active_statuses)
    ).order_by(models.Booking.booking_date.desc(), models.Booking.queue_number.asc()).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active queue booking found for farmer '{farmer.name}' ({phone_number})."
        )

    # Compute farmers ahead in queue at that center on that date
    farmers_ahead = db.query(models.Booking).filter(
        models.Booking.center_id == booking.center_id,
        models.Booking.booking_date == booking.booking_date,
        models.Booking.status.in_(active_statuses),
        models.Booking.queue_number < booking.queue_number
    ).count()

    avg_duration = get_center_avg_processing_time(db, booking.center_id, booking.booking_date)
    estimated_wait_mins = round(farmers_ahead * avg_duration, 1)

    eta_str = booking.estimated_arrival_time.strftime("%I:%M %p, %d %b %Y") if booking.estimated_arrival_time else f"In approx {int(estimated_wait_mins)} mins"

    return schemas.ActiveFarmerBookingResponse(
        booking_id=booking.id,
        booking_reference=booking.booking_reference,
        queue_number=booking.queue_number,
        status=booking.status,
        farmer_name=farmer.name,
        farmer_phone=farmer.phone_number,
        center_name=booking.center.name if booking.center else f"Center #{booking.center_id}",
        center_district=booking.center.district if booking.center else "N/A",
        booking_date=booking.booking_date,
        crop_type=booking.crop_type,
        estimated_quantity_quintals=booking.estimated_quantity_quintals,
        dynamic_eta=eta_str,
        farmers_ahead_in_queue=farmers_ahead,
        estimated_wait_minutes=estimated_wait_mins
    )
