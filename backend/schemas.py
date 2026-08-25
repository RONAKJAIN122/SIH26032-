from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from models import BookingStatus, PaymentStatus


# -------------------------------------------------------------
# Centers Schemas
# -------------------------------------------------------------
class CenterBase(BaseModel):
    name: str = Field(..., example="Karnal Anaj Mandi")
    code: str = Field(..., example="MANDI-HR-001")
    district: str = Field(..., example="Karnal")
    state: str = Field(..., example="Haryana")
    daily_capacity_quintals: float = Field(..., gt=0, example=12000.0)
    is_active: bool = True


class CenterCreate(CenterBase):
    pass


class CenterResponse(CenterBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Farmers Schemas
# -------------------------------------------------------------
class FarmerBase(BaseModel):
    name: str = Field(..., example="Gurpreet Singh")
    phone_number: str = Field(..., example="9876543210")
    village: Optional[str] = Field(None, example="Taraori")
    district: str = Field(..., example="Karnal")
    state: str = Field(..., example="Haryana")
    has_linked_bank_account: bool = False
    bank_account_number: Optional[str] = Field(None, example="123456789012")
    ifsc_code: Optional[str] = Field(None, example="SBIN0001234")


class FarmerCreate(FarmerBase):
    pass


class FarmerResponse(FarmerBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Bookings & Queue Management Schemas
# -------------------------------------------------------------
class SlotBookingRequest(BaseModel):
    farmer_id: int = Field(..., example=1)
    center_id: int = Field(..., example=1)
    crop_type: str = Field("Wheat", example="Wheat")
    estimated_quantity_quintals: float = Field(..., gt=0, example=120.0)
    requested_date: date = Field(..., example="2026-08-26")


class SlotBookingResponse(BaseModel):
    booking_id: int
    booking_reference: str
    queue_number: int
    status: BookingStatus
    booking_date: date
    crop_type: str
    estimated_quantity_quintals: float
    estimated_arrival_time: Optional[datetime] = None
    estimated_arrival_time_formatted: Optional[str] = None
    center_name: str
    center_district: str
    farmer_name: str
    farmer_phone: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class StatusUpdateRequest(BaseModel):
    status: BookingStatus = Field(..., example=BookingStatus.CHECKED_IN)


class StatusUpdateResponse(BaseModel):
    booking_id: int
    booking_reference: str
    old_status: BookingStatus
    new_status: BookingStatus
    processing_duration_minutes: Optional[float] = None
    average_processing_time_minutes: float
    recalculated_queue_count: int
    message: str


class LiveQueueItem(BaseModel):
    booking_id: int
    booking_reference: str
    queue_number: int
    status: BookingStatus
    farmer_id: int
    farmer_name: str
    farmer_phone: str
    crop_type: str
    estimated_quantity_quintals: float
    dynamic_eta: Optional[str] = None
    farmers_ahead: int


class CenterLiveQueueResponse(BaseModel):
    center_id: int
    center_name: str
    date: date
    daily_capacity_quintals: float
    booked_capacity_quintals: float
    active_in_queue_count: int
    completed_today_count: int
    average_processing_time_minutes: float
    queue: List[LiveQueueItem]


class ActiveFarmerBookingResponse(BaseModel):
    booking_id: int
    booking_reference: str
    queue_number: int
    status: BookingStatus
    farmer_name: str
    farmer_phone: str
    center_name: str
    center_district: str
    booking_date: date
    crop_type: str
    estimated_quantity_quintals: float
    dynamic_eta: str
    farmers_ahead_in_queue: int
    estimated_wait_minutes: float


class BookingResponse(BaseModel):
    id: int
    booking_reference: str
    center_id: int
    farmer_id: int
    booking_date: date
    queue_number: int
    crop_type: str
    estimated_quantity_quintals: float
    status: BookingStatus
    estimated_arrival_time: Optional[datetime] = None
    created_at: datetime
    center: Optional[CenterResponse] = None
    farmer: Optional[FarmerResponse] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Payments Schemas
# -------------------------------------------------------------
class PaymentBase(BaseModel):
    booking_id: int = Field(..., example=1)
    amount: float = Field(..., gt=0, example=337500.0)


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    id: int
    status: PaymentStatus
    transaction_ref: Optional[str] = None
    payment_date: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Farmer Portal Schemas
# -------------------------------------------------------------
class FarmerBookingDetail(BaseModel):
    """Enriched booking record returned to the farmer portal."""
    booking_id: int
    booking_reference: str
    center_id: int
    center_name: str
    center_district: str
    queue_number: int
    booking_date: str
    crop_type: str
    estimated_quantity_quintals: float
    status: BookingStatus
    estimated_arrival_time: Optional[str] = None
    farmers_ahead: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)
