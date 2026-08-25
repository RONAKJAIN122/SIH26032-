import json
import asyncio
from datetime import date, datetime
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(tags=["WebSocket Dashboard"])


class ConnectionManager:
    """
    Manages all active WebSocket connections.
    Handles connect, disconnect, and broadcasting JSON messages to all clients.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection and register it."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Client connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection on disconnect."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] Client disconnected. Total active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        Broadcast a JSON message to ALL currently connected WebSocket clients.
        Silently removes any broken connections.
        """
        if not self.active_connections:
            return

        message_text = json.dumps(message, default=str)
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                print(f"[WS] Failed to send to client: {e}")
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a JSON message to a single client."""
        await websocket.send_text(json.dumps(message, default=str))


# Singleton manager — shared across all endpoints
manager = ConnectionManager()


def build_queue_broadcast_payload(db: Session, center_id: int, target_date: date) -> dict:
    """
    Fetches all bookings for a center & date and builds a JSON payload
    suitable for broadcasting to all connected WebSocket dashboard clients.
    """
    center = db.query(models.Center).filter(models.Center.id == center_id).first()
    if not center:
        return {}

    all_bookings = db.query(models.Booking).filter(
        models.Booking.center_id == center_id,
        models.Booking.booking_date == target_date
    ).order_by(models.Booking.queue_number.asc()).all()

    active_statuses = [
        models.BookingStatus.CONFIRMED,
        models.BookingStatus.CHECKED_IN,
        models.BookingStatus.WEIGHING,
    ]

    queue_items = []
    for b in all_bookings:
        farmer_name = b.farmer.name if b.farmer else f"Farmer #{b.farmer_id}"
        farmer_phone = b.farmer.phone_number if b.farmer else "N/A"
        eta_str = b.estimated_arrival_time.strftime("%I:%M %p") if b.estimated_arrival_time else "—"
        farmers_ahead = sum(
            1 for ob in all_bookings
            if ob.status in active_statuses and ob.queue_number < b.queue_number
        )
        queue_items.append({
            "booking_id": b.id,
            "booking_reference": b.booking_reference,
            "queue_number": b.queue_number,
            "farmer_id": b.farmer_id,
            "farmer_name": farmer_name,
            "farmer_phone": farmer_phone,
            "crop_type": b.crop_type,
            "estimated_quantity_quintals": b.estimated_quantity_quintals,
            "status": b.status.value,
            "dynamic_eta": eta_str,
            "farmers_ahead": farmers_ahead,
        })

    completed_count = sum(1 for b in all_bookings if b.status == models.BookingStatus.COMPLETED)
    cancelled_count = sum(1 for b in all_bookings if b.status == models.BookingStatus.CANCELLED)
    active_count = sum(1 for b in all_bookings if b.status in active_statuses)
    booked_qty = sum(b.estimated_quantity_quintals for b in all_bookings if b.status != models.BookingStatus.CANCELLED)

    return {
        "event": "QUEUE_UPDATE",
        "timestamp": datetime.utcnow().isoformat(),
        "center_id": center.id,
        "center_name": center.name,
        "center_district": center.district,
        "date": str(target_date),
        "summary": {
            "daily_capacity_quintals": center.daily_capacity_quintals,
            "booked_capacity_quintals": round(booked_qty, 1),
            "active_in_queue": active_count,
            "completed_today": completed_count,
            "cancelled_today": cancelled_count,
            "total_bookings": len(all_bookings),
        },
        "queue": queue_items,
    }


@router.websocket("/ws/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for the real-time Admin Dashboard.
    - Accepts a connection and immediately sends today's queue state.
    - Stays alive waiting for keepalive pings.
    - Broadcasts are triggered externally via `manager.broadcast()` when
      any booking status changes (called from routers/queue.py).
    """
    await manager.connect(websocket)

    try:
        # On connection, immediately push current queue state for all centers
        today = date.today()
        centers = db.query(models.Center).filter(models.Center.is_active == True).all()
        for center in centers:
            payload = build_queue_broadcast_payload(db, center.id, today)
            if payload:
                await manager.send_personal_message(payload, websocket)

        # Keep connection alive — listen for client keepalive pings
        while True:
            data = await websocket.receive_text()
            if data.strip().upper() == "PING":
                await websocket.send_text(json.dumps({"event": "PONG", "timestamp": datetime.utcnow().isoformat()}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        manager.disconnect(websocket)
