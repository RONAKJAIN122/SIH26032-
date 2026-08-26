import { useState, useEffect, useRef } from "react";
import BookingCard from "../components/BookingCard";
import ProfileModal from "../components/ProfileModal";

const API = "http://127.0.0.1:8000";
const MSP = 2275.0;

export default function FarmerDashboard({ farmer, onBookSlot, onLogout }) {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("active"); // "active" | "history"
  const [showProfile, setShowProfile] = useState(false);
  const isFirstLoad = useRef(true);

  const fetchBookings = async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    try {
      const res = await fetch(`${API}/api/farmers/${farmer.id}/bookings?limit=30`);
      if (res.ok) setBookings(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      if (showSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    // First load: show spinner
    fetchBookings(true).then(() => { isFirstLoad.current = false; });
    // Subsequent polls: silent refresh (no spinner flash)
    const interval = setInterval(() => fetchBookings(false), 15000);
    return () => clearInterval(interval);
  }, [farmer.id]);

  const activeStatuses = ["CONFIRMED", "CHECKED_IN", "WEIGHING"];
  const active  = bookings.filter(b => activeStatuses.includes(b.status));
  const history = bookings.filter(b => !activeStatuses.includes(b.status));

  // Summary stats
  const totalPayout = bookings
    .filter(b => b.status === "COMPLETED")
    .reduce((s, b) => s + b.estimated_quantity_quintals * MSP, 0);
  const totalCompleted = bookings.filter(b => b.status === "COMPLETED").length;

  const initials = farmer.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="page" style={{ paddingTop: "0" }}>
      {/* Top Nav */}
      <div className="top-nav">
        <div className="nav-logo">
          <span className="nav-logo-icon">🌾</span>
          <span className="nav-logo-text">SmartMandi</span>
        </div>
        <button
          className="nav-farmer-chip"
          onClick={() => setShowProfile(true)}
          title="View Farmer Profile"
        >
          <div className="nav-avatar">{initials}</div>
          {farmer.name.split(" ")[0]}
        </button>
      </div>

      {/* Profile Modal */}
      {showProfile && (
        <ProfileModal
          farmer={farmer}
          bookings={bookings}
          onClose={() => setShowProfile(false)}
          onLogout={onLogout}
        />
      )}

      {/* Greeting Hero */}
      <div style={{ marginBottom: "1.25rem" }}>
        <div className="card" style={{
          background: "linear-gradient(135deg, rgba(6,182,212,0.12), rgba(99,102,241,0.12))",
          border: "1px solid rgba(6,182,212,0.2)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" }}>
            <div>
              <p style={{ color: "#94a3b8", fontSize: "0.82rem", marginBottom: "0.2rem" }}>
                Namaste 👋
              </p>
              <h2 style={{ fontSize: "1.3rem", fontWeight: 700 }}>{farmer.name}</h2>
              <p style={{ color: "#64748b", fontSize: "0.82rem", marginTop: "0.2rem" }}>
                📍 {farmer.village ? `${farmer.village}, ` : ""}{farmer.district} · 📞 +91-{farmer.phone_number}
              </p>
              <div style={{ marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{
                  fontSize: "0.75rem", padding: "0.2rem 0.6rem", borderRadius: "9999px",
                  background: farmer.has_linked_bank_account ? "rgba(74,222,128,0.15)" : "rgba(251,191,36,0.12)",
                  color: farmer.has_linked_bank_account ? "#4ade80" : "#fbbf24",
                  border: `1px solid ${farmer.has_linked_bank_account ? "rgba(74,222,128,0.3)" : "rgba(251,191,36,0.25)"}`,
                }}>
                  {farmer.has_linked_bank_account ? "🏦 Bank Linked" : "⚠ Bank Not Linked"}
                </span>
              </div>
            </div>
            <button className="btn btn-primary"
              style={{ width: "auto", padding: "0.65rem 1.2rem", fontSize: "0.9rem" }}
              onClick={onBookSlot}>
              + Book Slot
            </button>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem", marginBottom: "1.25rem" }}>
        <div className="card" style={{ padding: "1rem", textAlign: "center" }}>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#22d3ee" }}>{active.length}</div>
          <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "0.2rem" }}>Active</div>
        </div>
        <div className="card" style={{ padding: "1rem", textAlign: "center" }}>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#4ade80" }}>{totalCompleted}</div>
          <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "0.2rem" }}>Completed</div>
        </div>
        <div className="card" style={{ padding: "1rem", textAlign: "center" }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#c084fc" }}>
            {totalPayout > 0 ? `${(totalPayout / 100000).toFixed(1)}L` : "—"}
          </div>
          <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "0.2rem" }}>Payout (Rs)</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {["active", "history"].map(tab => (
          <button key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              flex: 1, padding: "0.6rem", border: "1px solid",
              borderRadius: "10px", cursor: "pointer", fontWeight: 600,
              fontSize: "0.875rem", transition: "all 0.18s",
              background: activeTab === tab ? "rgba(34,211,238,0.12)" : "rgba(255,255,255,0.04)",
              borderColor: activeTab === tab ? "rgba(34,211,238,0.35)" : "rgba(255,255,255,0.10)",
              color: activeTab === tab ? "#22d3ee" : "#64748b",
            }}>
            {tab === "active" ? `Active Tokens (${active.length})` : `History (${history.length})`}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading && (
        <div style={{ textAlign: "center", padding: "2rem", color: "#475569" }}>
          <span className="spinner" style={{ borderTopColor: "#22d3ee" }} /> Loading...
        </div>
      )}

      {!loading && activeTab === "active" && (
        active.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: "2.5rem 1rem", color: "#475569" }}>
            <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>🎫</div>
            <p style={{ fontWeight: 500 }}>No active tokens</p>
            <p style={{ fontSize: "0.82rem", marginTop: "0.3rem" }}>
              Book a slot to get your queue token
            </p>
            <button className="btn btn-primary"
              style={{ marginTop: "1.25rem", maxWidth: "200px", margin: "1.25rem auto 0" }}
              onClick={onBookSlot}>
              + Book Slot Now
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {active.map(b => <BookingCard key={b.booking_id} booking={b} highlight />)}
          </div>
        )
      )}

      {!loading && activeTab === "history" && (
        history.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: "2.5rem 1rem", color: "#475569" }}>
            <p>No booking history yet.</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {history.map(b => <BookingCard key={b.booking_id} booking={b} />)}
          </div>
        )
      )}

      <div style={{ textAlign: "center", marginTop: "2rem", color: "#1e293b", fontSize: "0.75rem" }}>
        Refreshes every 15s · SIH26032
      </div>
    </div>
  );
}
