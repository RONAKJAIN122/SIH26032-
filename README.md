# 🌾 SIH26032 - SmartMandi Queue Manager

**Smart India Hackathon Project `SIH26032`**  
A full-stack, real-time procurement and smart queue management system designed to eliminate congestion, long wait times, and distress selling at grain markets (Mandis) across Punjab & Haryana.

---

## 📌 Features & Core Capabilities

- 🏛️ **Procurement Centers (Mandis):** Daily procurement capacity enforcement in quintals with database row-level locking to prevent overbooking.
- 👨‍🌾 **Farmer Registration & Profiles:** Linked bank accounts, mobile numbers, Aadhaar verification, and village/district mapping.
- ⏱️ **Dynamic Slot Booking & ETA:** Real-time token allocation, arrival time slotting, and automatic overflow date suggestions if a Mandi's capacity is full.
- 📊 **Dynamic Queue Advancement:** Real-time tracking through lifecycle states (`PENDING` $\rightarrow$ `CONFIRMED` $\rightarrow$ `CHECKED_IN` $\rightarrow$ `WEIGHING` $\rightarrow$ `COMPLETED` / `CANCELLED`) with automatic ETA recalculations based on live Mandi processing speeds.
- 💬 **WhatsApp & SMS Bot Webhook:** Twilio-powered webhook allowing farmers to text `STATUS` to receive live token numbers, farmers ahead, and dynamic arrival times without needing any mobile app.
- 💻 **Admin Dashboard:** Modern React + Vite interface with live backend status, active queue tokens, and Mandi capacities.

---

## 📁 Monorepo Structure

```text
SIH26032/
├── backend/
│   ├── main.py                  # FastAPI entry point & CORS configuration
│   ├── database.py              # SQLAlchemy engine with auto-fallback (PostgreSQL / SQLite)
│   ├── models.py                # Database models (Centers, Farmers, Bookings, Payments)
│   ├── schemas.py               # Pydantic validation schemas
│   ├── seed.py                  # Faker seed script (5 Mandis, 50 Farmers, Live Queue)
│   ├── requirements.txt         # Python dependencies
│   ├── routers/
│   │   ├── queue.py             # Slot booking, capacity locking & queue algorithms
│   │   └── bot.py               # Twilio WhatsApp webhook (POST /api/bot/whatsapp)
│   └── venv/                    # Python virtual environment (ignored in git)
├── admin-frontend/
│   ├── src/
│   │   ├── App.jsx              # Admin dashboard with live stats & token tables
│   │   ├── App.css              # Dark theme styling with pulse indicator
│   │   ├── index.css            # Global design tokens
│   │   └── main.jsx             # Vite entry point
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 🚀 Quickstart: Running Locally (Windows)

### 1. Backend Setup (FastAPI)
Open a PowerShell terminal:
```powershell
cd c:\CSE_BABY\SIH26032\backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# (Optional) Seed the database with 5 Mandis & 50 Farmers
python seed.py

# Start FastAPI server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- **API URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health & DB Status:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Frontend Setup (React + Vite)
Open a second PowerShell terminal:
```powershell
cd c:\CSE_BABY\SIH26032\admin-frontend

# Install dependencies (first time only)
npm install

# Start Vite dev server
npm run dev
```
- **Admin Dashboard:** [http://localhost:5173](http://localhost:5173)

---

## 🐘 PostgreSQL Connection Setup

By default, the backend connects to **PostgreSQL** on port `5432`. If PostgreSQL is not active, it automatically falls back to local `smartmandi.db` (SQLite) for instant offline development.

To use your local PostgreSQL server:
1. Create the database in PostgreSQL / pgAdmin:
   ```sql
   CREATE DATABASE smartmandi;
   ```
2. Create `backend/.env`:
   ```ini
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/smartmandi
   ```
3. Run the seed script:
   ```powershell
   python seed.py
   ```

---

## 📲 WhatsApp Bot Setup (Twilio + ngrok)

Farmers can text `STATUS` to your WhatsApp number to check their live queue status.

### Step 1: Start ngrok Tunnel
In a new terminal:
```powershell
# Install ngrok if not already installed
winget install ngrok

# Expose local FastAPI port 8000
ngrok http 8000
```
Copy the public HTTPS forwarding URL (e.g. `https://a1b2-c3d4.ngrok-free.app`).

### Step 2: Configure Twilio WhatsApp Sandbox
1. Open the [Twilio Console](https://console.twilio.com/) $\rightarrow$ **Messaging** $\rightarrow$ **Try it out** $\rightarrow$ **Send a WhatsApp message** (Sandbox Settings).
2. Under **"WHEN A MESSAGE COMES IN"**:
   - **URL:** `https://your-ngrok-url.ngrok-free.app/api/bot/whatsapp`
   - **Method:** `HTTP POST`
3. Click **Save**.

### Step 3: Test WhatsApp Bot
Send any of the following to your Twilio Sandbox WhatsApp number:
- `STATUS` $\rightarrow$ Returns live Mandi token number, status, farmers ahead in queue, and dynamic arrival ETA.
- `HELP` $\rightarrow$ Returns bilingual welcome and helpline instructions.

---

## 📡 API Reference Summary

### Queue & Slot Booking (`/api`)
- `POST /api/bookings`: Book procurement slot with daily capacity check & dynamic queue allocation.
- `PATCH /api/bookings/{id}/status`: Advance status (`CHECKED_IN`, `WEIGHING`, `COMPLETED`, `CANCELLED`) and recalculate ETAs for all waiting farmers.
- `GET /api/centers/{id}/live-queue`: Fetch live queue of active tokens for today.
- `GET /api/farmers/{phone}/active-booking`: Fetch real-time token and ETA by farmer's phone number.

### WhatsApp Bot Webhook
- `POST /api/bot/whatsapp`: Incoming Twilio webhook parsing `From` and `Body` (returns TwiML XML).

---

## 📋 Hackathon Roadmap & To-Do List

- [x] Monorepo structure (FastAPI + React Vite)
- [x] Database models (Centers, Farmers, Bookings, Payments)
- [x] Seeder script for 5 Punjab/Haryana Mandis and 50 Farmers
- [x] Daily capacity lock & slot booking algorithm
- [x] Real-time dynamic queue ETA recalculation
- [x] Twilio WhatsApp bot webhook for instant token queries
- [x] Admin frontend with live statistics & token monitors
- [ ] **Automated SMS Push Alerts:** Send automated SMS when a farmer is 3rd in line (`"Your turn is in ~30 mins"`).
- [ ] **Weighbridge IoT Integration:** Direct gross & tare weight capture for instant digital slips.
- [ ] **Direct Benefit Transfer (DBT) Payouts:** Integrate automated payments directly to linked bank accounts upon weighing completion.
