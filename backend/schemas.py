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
# Bookings Schemas
# -------------------------------------------------------------
class BookingBase(BaseModel):
    center_id: int = Field(..., example=1)
    farmer_id: int = Field(..., example=1)
    booking_date: date = Field(..., example="2026-08-26")
    crop_type: str = Field("Wheat", example="Wheat")
    estimated_quantity_quintals: float = Field(..., gt=0, example=150.0)


class BookingCreate(BookingBase):
    pass


class BookingStatusUpdate(BaseModel):
    status: BookingStatus = Field(..., example=BookingStatus.CHECKED_IN)


class BookingResponse(BookingBase):
    id: int
    booking_reference: str
    queue_number: int
    status: BookingStatus
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


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus = Field(..., example=PaymentStatus.SUCCESS)
    transaction_ref: Optional[str] = Field(None, example="TXN-20260826-001")


class PaymentResponse(PaymentBase):
    id: int
    status: PaymentStatus
    transaction_ref: Optional[str] = None
    payment_date: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
