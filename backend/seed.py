import random
from datetime import date, datetime, timedelta
from faker import Faker
from database import SessionLocal, engine, Base
from models import Center, Farmer, Booking, Payment, BookingStatus, PaymentStatus

# Initialize Faker with Indian locale
fake = Faker("en_IN")

# 5 Realistic Mandis in Haryana and Punjab
REALISTIC_CENTERS = [
    {
        "name": "Khanna Dana Mandi (Asia's Largest Grain Market)",
        "code": "MANDI-PB-KHN01",
        "district": "Ludhiana",
        "state": "Punjab",
        "daily_capacity_quintals": 18000.0,
        "is_active": True,
    },
    {
        "name": "Karnal Central Anaj Mandi",
        "code": "MANDI-HR-KRN01",
        "district": "Karnal",
        "state": "Haryana",
        "daily_capacity_quintals": 14000.0,
        "is_active": True,
    },
    {
        "name": "Ambala Cantt Grain Procurement Hub",
        "code": "MANDI-HR-AMB01",
        "district": "Ambala",
        "state": "Haryana",
        "daily_capacity_quintals": 9500.0,
        "is_active": True,
    },
    {
        "name": "Sirsa New Grain Market",
        "code": "MANDI-HR-SRS01",
        "district": "Sirsa",
        "state": "Haryana",
        "daily_capacity_quintals": 11000.0,
        "is_active": True,
    },
    {
        "name": "Jalandhar Cantonment Dana Mandi",
        "code": "MANDI-PB-JAL01",
        "district": "Jalandhar",
        "state": "Punjab",
        "daily_capacity_quintals": 8500.0,
        "is_active": True,
    },
]

PUNJAB_HARYANA_VILLAGES = [
    ("Taraori", "Karnal", "Haryana"),
    ("Nilokheri", "Karnal", "Haryana"),
    ("Gharaunda", "Karnal", "Haryana"),
    ("Samana", "Patiala", "Punjab"),
    ("Nabha", "Patiala", "Punjab"),
    ("Doraha", "Ludhiana", "Punjab"),
    ("Samrala", "Ludhiana", "Punjab"),
    ("Mullana", "Ambala", "Haryana"),
    ("Barara", "Ambala", "Haryana"),
    ("Rania", "Sirsa", "Haryana"),
    ("Ellanabad", "Sirsa", "Haryana"),
    ("Nakodar", "Jalandhar", "Punjab"),
    ("Phillaur", "Jalandhar", "Punjab"),
]

CROP_TYPES = ["Wheat (Kanak)", "Paddy (Basmati)", "Paddy (PR-126)", "Mustard (Sarson)"]


def seed_database():
    print("🌱 Initializing Database Tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check existing data to prevent duplicate seeds
        if db.query(Center).count() > 0:
            print("⚠️  Database already contains records. Skipping seed.")
            return

        print("\n🏛️  Seeding 5 Realistic Mandi Procurement Centers...")
        created_centers = []
        for center_data in REALISTIC_CENTERS:
            center = Center(**center_data)
            db.add(center)
            created_centers.append(center)
        db.commit()

        for c in created_centers:
            db.refresh(c)
            print(f"  ✓ Added Mandi: {c.name} (Capacity: {c.daily_capacity_quintals} quintals)")

        print("\n👨‍🌾 Seeding 50 Dummy Farmers from Haryana & Punjab...")
        created_farmers = []
        used_phones = set()

        for i in range(50):
            # Generate unique Indian mobile number (e.g. 98xxxxxxx)
            while True:
                phone = f"{random.choice(['98', '97', '94', '99', '87', '70'])}{random.randint(10000000, 99999999)}"
                if phone not in used_phones:
                    used_phones.add(phone)
                    break

            village_info = random.choice(PUNJAB_HARYANA_VILLAGES)
            has_bank = random.random() < 0.85  # 85% farmers have linked bank account

            bank_acc = f"30{random.randint(1000000000, 9999999999)}" if has_bank else None
            ifsc = random.choice(["SBIN0001234", "PUNB0123400", "HDFC0000456"]) if has_bank else None

            farmer = Farmer(
                name=fake.name(),
                phone_number=phone,
                village=village_info[0],
                district=village_info[1],
                state=village_info[2],
                has_linked_bank_account=has_bank,
                bank_account_number=bank_acc,
                ifsc_code=ifsc
            )
            db.add(farmer)
            created_farmers.append(farmer)

        db.commit()
        for f in created_farmers:
            db.refresh(f)

        print(f"  ✓ Successfully seeded 50 farmers!")

        print("\n📦 Seeding Sample Live Bookings & Dynamic Queue Numbers...")
        today = date.today()
        created_bookings = []

        for i in range(15):
            center = random.choice(created_centers)
            farmer = random.choice(created_farmers)
            qty = round(random.uniform(40.0, 250.0), 1)
            crop = random.choice(CROP_TYPES)
            booking_date = today + timedelta(days=random.randint(0, 2))
            queue_no = i + 1

            booking = Booking(
                booking_reference=f"BK-{booking_date.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                center_id=center.id,
                farmer_id=farmer.id,
                booking_date=booking_date,
                queue_number=queue_no,
                crop_type=crop,
                estimated_quantity_quintals=qty,
                status=random.choice([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.IN_PROGRESS])
            )
            db.add(booking)
            created_bookings.append(booking)

        db.commit()

        print("\n💳 Seeding Payments for completed/in-progress Bookings...")
        # MSP approximately Rs 2275 per quintal for wheat
        MSP_PER_QUINTAL = 2275.0
        for b in created_bookings[:8]:
            db.refresh(b)
            amount = round(b.estimated_quantity_quintals * MSP_PER_QUINTAL, 2)
            payment = Payment(
                booking_id=b.id,
                amount=amount,
                status=random.choice([PaymentStatus.SUCCESS, PaymentStatus.PROCESSING, PaymentStatus.PENDING]),
                transaction_ref=f"TXN-SIH-{random.randint(10000000, 99999999)}",
                payment_date=datetime.utcnow() if random.choice([True, False]) else None
            )
            db.add(payment)

        db.commit()
        print("  ✓ Successfully created sample bookings and payments!")

        print("\n🎉 Database Seeding Completed Successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error while seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
