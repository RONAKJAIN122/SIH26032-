import { useState, useEffect } from "react";
import Dashboard from "./Dashboard";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [view, setView] = useState("overview"); // "overview" | "dashboard"
  const [healthStatus, setHealthStatus] = useState("Checking...");
  const [backendDetails, setBackendDetails] = useState(null);
  const [centers, setCenters] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [isOnline, setIsOnline] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  const fetchHealthAndData = async () => {
    setHealthStatus("Connecting...");
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      if (data.status === "online") {
        setHealthStatus("System Online");
        setIsOnline(true);
        setBackendDetails(data);

        const [centersRes, bookingsRes] = await Promise.all([
          fetch(`${API_BASE}/centers`),
          fetch(`${API_BASE}/bookings`),
        ]);
        if (centersRes.ok) setCenters(await centersRes.json());
        if (bookingsRes.ok) setBookings(await bookingsRes.json());
      } else {
        setHealthStatus("Unexpected Response");
        setIsOnline(false);
      }
    } catch (err) {
      setHealthStatus("System Offline");
      setIsOnline(false);
      setError("Unable to connect to FastAPI backend at http://127.0.0.1:8000.");
    }
  };

  useEffect(() => {
    fetchHealthAndData();
  }, []);

  // Render the real-time dashboard in full view
  if (view === "dashboard") {
    return (
      <div>
        <button className="back-btn" onClick={() => setView("overview")}>
          ← Back to Overview
        </button>
        <Dashboard />
      </div>
    );
  }

  return (
    <div className="container">
      <header className="header">
        <div className="badge">SIH26032 • Live System</div>
        <h1>🌾 SmartMandi Queue Manager</h1>
        <p className="subtitle">Real-time Grain Procurement & Smart Mandi Queue Management</p>
      </header>

      {/* Connectivity Banner */}
      <div className="card status-card">
        <div className="status-container">
          <span className={`status-indicator ${isOnline ? "online" : "offline"}`}></span>
          <span className="status-text">{healthStatus}</span>
          {backendDetails?.database && (
            <span className="db-badge">Database: {backendDetails.database}</span>
          )}
        </div>
        <div className="header-actions">
          <button className="refresh-btn" onClick={fetchHealthAndData}>
            🔄 Refresh
          </button>
          <button className="dashboard-btn" onClick={() => setView("dashboard")}>
            📊 Open Live Dashboard
          </button>
        </div>
      </div>

      {error && <div className="error-box"><p>{error}</p></div>}

      {/* Stats Grid */}
      {backendDetails?.stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-icon">🏛️</span>
            <span className="stat-value">{backendDetails.stats.total_centers}</span>
            <span className="stat-label">Procurement Centers</span>
          </div>
          <div className="stat-card">
            <span className="stat-icon">👨‍🌾</span>
            <span className="stat-value">{backendDetails.stats.total_farmers}</span>
            <span className="stat-label">Registered Farmers</span>
          </div>
          <div className="stat-card">
            <span className="stat-icon">📋</span>
            <span className="stat-value">{backendDetails.stats.total_bookings}</span>
            <span className="stat-label">Active Bookings</span>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === "overview" ? "active" : ""}`}
          onClick={() => setActiveTab("overview")}
        >
          🏛️ Mandi Centers ({centers.length})
        </button>
        <button
          className={`tab-btn ${activeTab === "queue" ? "active" : ""}`}
          onClick={() => setActiveTab("queue")}
        >
          ⏱️ Live Queue ({bookings.length})
        </button>
      </div>

      {/* Tab: Centers */}
      {activeTab === "overview" && (
        <section className="card list-section">
          <h2>Haryana & Punjab Procurement Mandis</h2>
          <div className="items-grid">
            {centers.map((c) => (
              <div key={c.id} className="item-card">
                <div className="item-header">
                  <h3>{c.name}</h3>
                  <span className="code-pill">{c.code}</span>
                </div>
                <p className="item-location">📍 {c.district}, {c.state}</p>
                <div className="capacity-bar">
                  <span>Daily Capacity: <strong>{c.daily_capacity_quintals.toLocaleString()} Q</strong></span>
                  <span className="active-tag">{c.is_active ? "● Operational" : "Closed"}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Tab: Live Queue */}
      {activeTab === "queue" && (
        <section className="card list-section">
          <h2>Active Farmer Queue Tokens</h2>
          <div className="table-wrapper">
            <table className="queue-table">
              <thead>
                <tr>
                  <th>Token #</th>
                  <th>Booking Ref</th>
                  <th>Date</th>
                  <th>Crop</th>
                  <th>Est. Quantity</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {bookings.map((b) => (
                  <tr key={b.id}>
                    <td><span className="token-badge">#{b.queue_number}</span></td>
                    <td className="mono">{b.booking_reference}</td>
                    <td>{b.booking_date}</td>
                    <td>{b.crop_type}</td>
                    <td><strong>{b.estimated_quantity_quintals} Q</strong></td>
                    <td>
                      <span className={`status-pill ${b.status.toLowerCase()}`}>
                        {b.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="admin-cta">
            <button className="dashboard-btn large" onClick={() => setView("dashboard")}>
              📊 Open Real-Time Admin Dashboard →
            </button>
          </div>
        </section>
      )}

      <footer className="footer">
        <p>Smart India Hackathon • Project SIH26032</p>
        <p className="subtext">FastAPI + PostgreSQL / SQLite + React Vite</p>
      </footer>
    </div>
  );
}

export default App;
