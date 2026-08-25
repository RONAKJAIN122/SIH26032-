import re
from datetime import date, datetime
from fastapi import APIRouter, Depends, Form, Response, status
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

from database import get_db
import models
from routers.queue import get_center_avg_processing_time

router = APIRouter(
    prefix="/api/bot",
    tags=["WhatsApp & SMS Bot Webhooks"]
)


def normalize_phone_number(raw_phone: str) -> str:
    """
    Extract clean 10-digit Indian phone number from Twilio From format.
    Handles 'whatsapp:+919876543210', '+919876543210', '09876543210', etc.
    """
    cleaned = raw_phone.replace("whatsapp:", "").strip()
    digits = re.sub(r"\D", "", cleaned)
    if digits.startswith("91") and len(digits) == 12:
        return digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        return digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


@router.post("/whatsapp", status_code=status.HTTP_200_OK)
def whatsapp_webhook(
    From: str = Form(..., description="Twilio sender phone number e.g. whatsapp:+919876543210"),
    Body: str = Form(..., description="Incoming message body from user"),
    db: Session = Depends(get_db)
):
    """
    Twilio Webhook for WhatsApp / SMS bot interaction:
    1. Parses incoming Form data ('From' and 'Body').
    2. Processes 'STATUS' command to return live Mandi token, queue position & ETA.
    3. Returns TwiML XML response for Twilio Messaging API.
    """
    resp = MessagingResponse()
    incoming_text = Body.strip().upper()
    phone_number = normalize_phone_number(From)

    # -------------------------------------------------------------
    # 1. Handle "STATUS" Command
    # -------------------------------------------------------------
    if "STATUS" in incoming_text or "TOKEN" in incoming_text:
        farmer = db.query(models.Farmer).filter(
            (models.Farmer.phone_number == phone_number) |
            (models.Farmer.phone_number.endswith(phone_number))
        ).first()

        if not farmer:
            reply_msg = (
                "❌ *Farmer Not Found*\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"The mobile number *{phone_number}* is not registered in the SmartMandi database.\n\n"
                "Please register with your Aadhaar/Bank details at your local Mandi office."
            )
            resp.message(reply_msg)
            return Response(content=str(resp), media_type="application/xml")

        # Query active booking for this farmer
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
            reply_msg = (
                f"🌾 *Namaste {farmer.name}* 🙏\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "You currently have *no active queue bookings* for today.\n\n"
                "👉 To book a procurement slot, visit your Mandi portal or contact the helpdesk."
            )
            resp.message(reply_msg)
            return Response(content=str(resp), media_type="application/xml")

        # Calculate live queue position & dynamic ETA
        farmers_ahead = db.query(models.Booking).filter(
            models.Booking.center_id == booking.center_id,
            models.Booking.booking_date == booking.booking_date,
            models.Booking.status.in_(active_statuses),
            models.Booking.queue_number < booking.queue_number
        ).count()

        avg_pace = get_center_avg_processing_time(db, booking.center_id, booking.booking_date)
        est_wait_mins = round(farmers_ahead * avg_pace, 1)

        eta_formatted = (
            booking.estimated_arrival_time.strftime("%I:%M %p, %d %b %Y")
            if booking.estimated_arrival_time
            else f"In approx {int(est_wait_mins)} mins"
        )

        center_name = booking.center.name if booking.center else f"Center #{booking.center_id}"
        center_district = booking.center.district if booking.center else "Punjab/Haryana"

        reply_msg = (
            "🌾 *SmartMandi Live Queue Status* 🌾\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Farmer:* {farmer.name}\n"
            f"🏛️ *Mandi:* {center_name} ({center_district})\n"
            f"🎫 *Token / Queue #:* *#{booking.queue_number}*\n"
            f"🔖 *Ref Code:* `{booking.booking_reference}`\n"
            f"📦 *Crop:* {booking.crop_type} ({booking.estimated_quantity_quintals} Q)\n"
            f"📊 *Status:* *{booking.status.value}*\n"
            f"👥 *Farmers Ahead:* *{farmers_ahead}*\n"
            f"⏱️ *Dynamic Slot ETA:* *{eta_formatted}*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 _Reply 'STATUS' anytime to get updated queue timings._"
        )
        resp.message(reply_msg)
        return Response(content=str(resp), media_type="application/xml")

    # -------------------------------------------------------------
    # 2. Fallback / Welcome Instructions
    # -------------------------------------------------------------
    fallback_msg = (
        "🌾 *Welcome to SmartMandi Queue Bot* 🌾\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Here are the commands you can use:\n\n"
        "👉 Send *STATUS* — Check your live token, queue number & arrival ETA.\n"
        "👉 Send *HELP* — Get Mandi helpline assistance.\n\n"
        "मंडी टोकन और समय जानने के लिए *STATUS* लिखकर भेजें।\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Smart India Hackathon • Project SIH26032"
    )
    resp.message(fallback_msg)
    return Response(content=str(resp), media_type="application/xml")
