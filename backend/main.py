from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models
import schemas

# Automatically create tables if they do not exist
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title="SmartMandi Queue Manager API",
    description="Backend API for SIH26032 - Smart India Hackathon Procurement & Queue System",
    version="1.0.0"
)

# CORS Configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Root & Health Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Welcome to SmartMandi Queue Manager API"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint that verifies API & Database connectivity."""
    centers_count = db.query(models.Center).count()
    farmers_count = db.query(models.Farmer).count()
    bookings_count = db.query(models.Booking).count()

    return {
        "status": "online",
        "service": "SmartMandi Queue Manager",
        "message": "System Online",
        "database": "Connected",
        "stats": {
            "total_centers": centers_count,
            "total_farmers": farmers_count,
            "total_bookings": bookings_count
        }
    }


# --- Centers Endpoints ---
@app.get("/centers", response_model=List[schemas.CenterResponse])
def get_centers(db: Session = Depends(get_db)):
    """List all procurement centers."""
    return db.query(models.Center).all()


@app.post("/centers", response_model=schemas.CenterResponse, status_code=status.HTTP_201_CREATED)
def create_center(center: schemas.CenterCreate, db: Session = Depends(get_db)):
    """Create a new procurement center."""
    existing = db.query(models.Center).filter(models.Center.code == center.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Center code already registered.")
    new_center = models.Center(**center.model_dump())
    db.add(new_center)
    db.commit()
    db.refresh(new_center)
    return new_center


# --- Farmers Endpoints ---
@app.get("/farmers", response_model=List[schemas.FarmerResponse])
def get_farmers(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List farmers with pagination."""
    return db.query(models.Farmer).offset(skip).limit(limit).all()


@app.post("/farmers", response_model=schemas.FarmerResponse, status_code=status.HTTP_201_CREATED)
def create_farmer(farmer: schemas.FarmerCreate, db: Session = Depends(get_db)):
    """Register a new farmer."""
    existing = db.query(models.Farmer).filter(models.Farmer.phone_number == farmer.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Farmer phone number already registered.")
    new_farmer = models.Farmer(**farmer.model_dump())
    db.add(new_farmer)
    db.commit()
    db.refresh(new_farmer)
    return new_farmer


# --- Bookings Endpoints ---
@app.get("/bookings", response_model=List[schemas.BookingResponse])
def get_bookings(db: Session = Depends(get_db)):
    """List all bookings with queue positions."""
    return db.query(models.Booking).all()


# --- Payments Endpoints ---
@app.get("/payments", response_model=List[schemas.PaymentResponse])
def get_payments(db: Session = Depends(get_db)):
    """List all payment records."""
    return db.query(models.Payment).all()
