import { useState, useEffect } from "react";

const API = "http://127.0.0.1:8000";

const CROPS = [
  "Wheat (Kanak)",
  "Paddy (Basmati)",
  "Paddy (PR-126)",
  "Mustard (Sarson)",
  "Maize (Makka)",
  "Barley (Jau)",
];

// Capacity bar component
function CapacityBar({ booked, capacity }) {
  const pct = Math.min(100, (booked / capacity) * 100);
  const color = pct > 90 ? "#f87171" : pct > 70 ? "#fbbf24" : "#4ade80";
  return (
    <div style={{ marginTop: "0.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.3rem", fontSize: "0.75rem", color: "#64748b" }}>
        <span>{booked.toLocaleString()} Q booked</span>
        <span style={{ color }}>{(capacity - booked).toLocaleString()} Q free</span>
      </div>
      <div style={{ height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "9999px", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: "9999px", transition: "width 0.4s ease" }} />
      </div>
    </div>
  );
}

// Booking confirmation screen
function ConfirmationCard({ booking, onDone }) {
  const MSP = 2275.0;
  const estPayout = (booking.estimated_quantity_quintals * MSP).toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

  return (
    <div className="page" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
      <div className="card" style={{
        textAlign: "center", padding: "2rem 1.5rem",
        background: "linear-gradient(135deg, rgba(74,222,128,0.08), rgba(34,211,238,0.08))",
        border: "1px solid rgba(74,222,128,0.25)",
      }}>
        <div style={{ fontSize: "3rem", marginBottom: "0.75rem" }}>🎉</div>
        <h2 style={{ fontSize: "1.3rem", fontWeight: 800, color: "#4ade80" }}>Slot Booked!</h2>
        <p style={{ color: "#64748b", fontSize: "0.88rem", margin: "0.4rem 0 1.5rem" }}>
          Your token has been assigned
        </p>

        {/* Big Token Number */}
        <div style={{
          background: "rgba(34,211,238,0.1)", border: "2px solid rgba(34,211,238,0.3)",
          borderRadius: "16px", padding: "1.25rem", marginBottom: "1.25rem",
        }}>
          <p style={{ color: "#94a3b8", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Your Queue Token</p>
          <div style={{ fontSize: "3.5rem", fontWeight: 900, color: "#22d3ee", lineHeight: 1 }}>
            #{booking.queue_number}
          </div>
          <p style={{ color: "#64748b", fontSize: "0.82rem", marginTop: "0.4rem" }}>
            Ref: <span style={{ fontFamily: "monospace", color: "#94a3b8" }}>{booking.booking_reference}</span>
          </p>
        </div>

        {/* Details grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1.5rem", textAlign: "left" }}>
          {[
            { label: "📅 Date",    value: booking.booking_date },
            { label: "🕐 ETA",    value: booking.estimated_arrival_time_formatted?.split(",")[0] || "—" },
            { label: "🌾 Crop",   value: booking.crop_type },
            { label: "⚖ Qty",    value: `${booking.estimated_quantity_quintals} Q` },
            { label: "🏛 Mandi",  value: booking.center_district },
            { label: "💰 Est. MSP", value: estPayout },
          ].map(({ label, value }) => (
            <div key={label} style={{ background: "rgba(255,255,255,0.04)", borderRadius: "10px", padding: "0.65rem 0.85rem" }}>
              <div style={{ fontSize: "0.72rem", color: "#475569", marginBottom: "0.2rem" }}>{label}</div>
              <div style={{ fontSize: "0.88rem", fontWeight: 600 }}>{value}</div>
            </div>
          ))}
        </div>

        <div style={{
          background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.2)",
          borderRadius: "10px", padding: "0.75rem", marginBottom: "1.25rem",
          fontSize: "0.82rem", color: "#fbbf24",
        }}>
          📲 You will receive an SMS when it's your turn
        </div>

        <button className="btn btn-primary" onClick={onDone}>
          View My Dashboard →
        </button>
      </div>
    </div>
  );
}

export default function BookSlotPage({ farmer, onBack, onBooked }) {
  const [centers, setCenters] = useState([]);
  const [selectedCenter, setSelectedCenter] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [bookingDate, setBookingDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [cropType, setCropType] = useState(CROPS[0]);
  const [quantity, setQuantity] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingAvail, setLoadingAvail] = useState(false);
  const [error, setError] = useState("");
  const [confirmedBooking, setConfirmedBooking] = useState(null);

  // Load centers on mount
  useEffect(() => {
    fetch(`${API}/centers`)
      .then(r => r.json())
      .then(data => {
        const active = data.filter(c => c.is_active);
        setCenters(active);
        if (active.length > 0) setSelectedCenter(active[0]);
      })
      .catch(() => setError("Could not load centers."));
  }, []);

  // Load availability when center or date changes
  useEffect(() => {
    if (!selectedCenter || !bookingDate) return;
    setLoadingAvail(true);
    fetch(`${API}/api/farmers/centers/${selectedCenter.id}/availability?booking_date=${bookingDate}`)
      .then(r => r.json())
      .then(setAvailability)
      .catch(() => setAvailability(null))
      .finally(() => setLoadingAvail(false));
  }, [selectedCenter, bookingDate]);

  const handleBook = async (e) => {
    e.preventDefault();
    const qty = parseFloat(quantity);
    if (!qty || qty <= 0) { setError("Enter a valid quantity."); return; }
    if (!selectedCenter) { setError("Please select a Mandi center."); return; }
    if (!availability?.is_available) { setError("This center is fully booked for the selected date."); return; }

    setError(""); setLoading(true);
    try {
      const res = await fetch(`${API}/api/bookings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          farmer_id: farmer.id,
          center_id: selectedCenter.id,
          crop_type: cropType,
          estimated_quantity_quintals: qty,
          requested_date: bookingDate,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setConfirmedBooking(data);
      } else {
        setError(data.detail || "Booking failed. Please try again.");
      }
    } catch {
      setError("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  };

  // Show confirmation screen after successful booking
  if (confirmedBooking) {
    return <ConfirmationCard booking={confirmedBooking} onDone={onBooked} />;
  }

  // Min date = today
  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="page" style={{ paddingTop: "0" }}>
      {/* Nav */}
      <div className="top-nav">
        <button className="btn btn-ghost" style={{ padding: 0, width: "auto" }} onClick={onBack}>
          ← Dashboard
        </button>
        <span style={{ fontSize: "0.88rem", color: "#64748b" }}>Book Slot</span>
      </div>

      <h2 style={{ fontWeight: 700, fontSize: "1.2rem", marginBottom: "1.25rem" }}>
        Book Procurement Slot
      </h2>

      <form onSubmit={handleBook} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>

        {/* Center Selection */}
        <div>
          <p className="section-title">Select Mandi Center</p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {centers.map(c => (
              <button key={c.id} type="button"
                onClick={() => setSelectedCenter(c)}
                style={{
                  display: "flex", alignItems: "flex-start", justifyContent: "space-between",
                  padding: "0.9rem 1rem", border: "1px solid",
                  borderRadius: "12px", cursor: "pointer", textAlign: "left",
                  background: selectedCenter?.id === c.id ? "rgba(34,211,238,0.08)" : "rgba(255,255,255,0.03)",
                  borderColor: selectedCenter?.id === c.id ? "rgba(34,211,238,0.4)" : "rgba(255,255,255,0.08)",
                  transition: "all 0.18s",
                }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.92rem", color: "#f1f5f9" }}>{c.name}</div>
                  <div style={{ fontSize: "0.78rem", color: "#64748b", marginTop: "0.15rem" }}>
                    📍 {c.district}, {c.state}
                  </div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0, marginLeft: "0.75rem" }}>
                  <div style={{ fontSize: "0.72rem", color: "#475569" }}>Capacity</div>
                  <div style={{ fontWeight: 700, color: "#94a3b8", fontSize: "0.88rem" }}>
                    {(c.daily_capacity_quintals / 1000).toFixed(0)}K Q
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Date Picker */}
        <div className="input-group">
          <label className="input-label">📅 Booking Date</label>
          <input
            className="input-field"
            type="date"
            min={today}
            value={bookingDate}
            onChange={e => setBookingDate(e.target.value)}
            required
            style={{ colorScheme: "dark" }}
          />
        </div>

        {/* Availability indicator */}
        {selectedCenter && bookingDate && (
          <div className="card" style={{ padding: "0.9rem 1rem" }}>
            {loadingAvail ? (
              <div style={{ color: "#475569", fontSize: "0.85rem" }}>Checking availability...</div>
            ) : availability ? (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                    {availability.center_name}
                  </span>
                  <span style={{
                    fontSize: "0.72rem", padding: "0.2rem 0.6rem", borderRadius: "9999px",
                    background: availability.is_available ? "rgba(74,222,128,0.12)" : "rgba(248,113,113,0.12)",
                    color: availability.is_available ? "#4ade80" : "#f87171",
                    border: `1px solid ${availability.is_available ? "rgba(74,222,128,0.3)" : "rgba(248,113,113,0.3)"}`,
                  }}>
                    {availability.is_available ? "Slots Available" : "Fully Booked"}
                  </span>
                </div>
                <CapacityBar
                  booked={availability.booked_quintals}
                  capacity={availability.daily_capacity_quintals}
                />
                <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "#475569" }}>
                  {availability.total_bookings_today} bookings · {availability.utilization_percent}% full
                </div>
              </>
            ) : null}
          </div>
        )}

        {/* Crop Type */}
        <div className="input-group">
          <label className="input-label">🌾 Crop Type</label>
          <select className="input-field" value={cropType}
            onChange={e => setCropType(e.target.value)}>
            {CROPS.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>

        {/* Quantity */}
        <div className="input-group">
          <label className="input-label">⚖ Estimated Quantity (Quintals)</label>
          <div style={{ position: "relative" }}>
            <input
              className="input-field"
              type="number"
              placeholder="e.g. 120"
              min="1"
              max="2000"
              step="0.1"
              value={quantity}
              onChange={e => setQuantity(e.target.value)}
              style={{ paddingRight: "3.5rem" }}
              required
            />
            <span style={{
              position: "absolute", right: "1rem", top: "50%", transform: "translateY(-50%)",
              color: "#475569", fontSize: "0.82rem", pointerEvents: "none",
            }}>Q</span>
          </div>

          {/* MSP estimate */}
          {quantity && parseFloat(quantity) > 0 && (
            <div style={{
              marginTop: "0.4rem", padding: "0.5rem 0.85rem",
              background: "rgba(192,132,252,0.08)", border: "1px solid rgba(192,132,252,0.2)",
              borderRadius: "8px", fontSize: "0.82rem", color: "#c084fc",
            }}>
              Estimated MSP payout: <strong>
                Rs {(parseFloat(quantity) * 2275).toLocaleString("en-IN")}
              </strong> (@ Rs 2,275/Q)
            </div>
          )}
        </div>

        {error && <div className="error-msg">{error}</div>}

        <button type="submit" className="btn btn-primary"
          disabled={loading || (availability && !availability.is_available)}>
          {loading ? <span className="spinner" /> : "Confirm Booking →"}
        </button>

        <p style={{ textAlign: "center", fontSize: "0.78rem", color: "#334155" }}>
          You'll receive your token number and ETA immediately after booking
        </p>
      </form>
    </div>
  );
}
