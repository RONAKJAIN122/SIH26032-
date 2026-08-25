from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="SmartMandi Queue Manager API",
    description="Backend API for SIH26032 - SmartMandi Queue Manager",
    version="1.0.0"
)

# Configure CORS so the React frontend can communicate with the backend
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


@app.get("/")
def read_root():
    return {"message": "Welcome to SmartMandi Queue Manager API"}


@app.get("/health")
def health_check():
    """Health check endpoint to verify backend status."""
    return {
        "status": "online",
        "service": "SmartMandi Queue Manager",
        "message": "System Online"
    }
