import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Enum as SqlEnum,
)
from sqlalchemy.orm import relationship
from database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# 1. Centers Table
class Center(Base):
    __tablename__ = "centers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    district = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    daily_capacity_quintals = Column(Float, nullable=False, default=10000.0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    bookings = relationship("Booking", back_populates="center", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Center id={self.id} name='{self.name}' capacity={self.daily_capacity_quintals}q>"


# 2. Farmers Table
class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone_number = Column(String(15), unique=True, nullable=False, index=True)
    village = Column(String(150), nullable=True)
    district = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    has_linked_bank_account = Column(Boolean, default=False, nullable=False)
    bank_account_number = Column(String(30), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    bookings = relationship("Booking", back_populates="farmer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Farmer id={self.id} name='{self.name}' phone='{self.phone_number}'>"


# 3. Bookings Table
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_reference = Column(String(50), unique=True, nullable=False, index=True)
    center_id = Column(Integer, ForeignKey("centers.id"), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    booking_date = Column(Date, nullable=False, index=True)
    queue_number = Column(Integer, nullable=False)
    crop_type = Column(String(100), nullable=False, default="Wheat")
    estimated_quantity_quintals = Column(Float, nullable=False)
    status = Column(
        SqlEnum(BookingStatus, name="booking_status_enum", create_type=False),
        default=BookingStatus.PENDING,
        nullable=False,
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    center = relationship("Center", back_populates="bookings")
    farmer = relationship("Farmer", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Booking ref='{self.booking_reference}' queue={self.queue_number} status={self.status}>"


# 4. Payments Table
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(
        SqlEnum(PaymentStatus, name="payment_status_enum", create_type=False),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True
    )
    transaction_ref = Column(String(100), unique=True, nullable=True, index=True)
    payment_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    booking = relationship("Booking", back_populates="payment")

    def __repr__(self):
        return f"<Payment id={self.id} booking_id={self.booking_id} amount={self.amount} status={self.status}>"
