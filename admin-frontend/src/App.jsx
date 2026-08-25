import { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [healthStatus, setHealthStatus] = useState("Checking...");
  const [backendDetails, setBackendDetails] = useState(null);
  const [isOnline, setIsOnline] = useState(false);
  const [error, setError] = useState(null);

  const fetchHealth = async () => {
    setHealthStatus("Connecting...");
    setError(null);
    try {
      const response = await fetch("http://127.0.0.1:8000/health");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      if (data.status === "online") {
        setHealthStatus("System Online");
        setIsOnline(true);
        setBackendDetails(data);
      } else {
        setHealthStatus("Unexpected Response");
        setIsOnline(false);
      }
    } catch (err) {
      console.error("Failed to connect to backend:", err);
      setHealthStatus("System Offline");
      setIsOnline(false);
      setError("Unable to connect to FastAPI backend at http://127.0.0.1:8000. Make sure uvicorn is running.");
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="container">
      <header className="header">
        <div className="badge">SIH26032</div>
        <h1>🌾 SmartMandi Queue Manager</h1>
        <p className="subtitle">Admin Dashboard & Live Queue Monitoring</p>
      </header>

      <main className="card">
        <h2>Backend Connectivity</h2>
        <div className="status-container">
          <span className={`status-indicator ${isOnline ? "online" : "offline"}`}></span>
          <span className="status-text">{healthStatus}</span>
        </div>

        {backendDetails && (
          <div className="details-box">
            <p><strong>Service:</strong> {backendDetails.service}</p>
            <p><strong>Status:</strong> {backendDetails.status}</p>
            <p><strong>Message:</strong> {backendDetails.message}</p>
          </div>
        )}

        {error && (
          <div className="error-box">
            <p>{error}</p>
          </div>
        )}

        <button className="refresh-btn" onClick={fetchHealth}>
          🔄 Recheck Status
        </button>
      </main>

      <footer className="footer">
        <p>Smart India Hackathon • Project SIH26032</p>
      </footer>
    </div>
  );
}

export default App;
