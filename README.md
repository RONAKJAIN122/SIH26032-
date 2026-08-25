# SIH26032 - SmartMandi Queue Manager 🌾

A monorepo setup for **SmartMandi Queue Manager** (Smart India Hackathon Project `SIH26032`).

---

## 📁 Repository Structure

```text
SIH26032/
├── backend/                  # FastAPI Python backend
│   ├── main.py              # Application entry point with CORS & /health
│   ├── requirements.txt     # Python dependencies (fastapi, uvicorn)
│   └── venv/                # Python virtual environment (ignored in git)
├── admin-frontend/          # React + Vite admin dashboard
│   ├── src/
│   │   ├── App.jsx          # Root component checking backend health
│   │   ├── App.css          # Component styling
│   │   ├── main.jsx         # Vite React entrypoint
│   │   └── index.css        # Global CSS theme
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 🚀 How to Run Locally (Windows PowerShell)

### 1. Start Backend (FastAPI)
Open a new PowerShell terminal:
```powershell
cd c:\CSE_BABY\SIH26032\backend
# Activate virtual environment
.\venv\Scripts\Activate.ps1
# Run FastAPI with live reload
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- API URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Interactive API Docs (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Start Frontend (React + Vite)
Open a second PowerShell terminal:
```powershell
cd c:\CSE_BABY\SIH26032\admin-frontend
npm run dev
```
- Frontend URL: [http://localhost:5173](http://localhost:5173)
