const STATUS_STEPS = ["CONFIRMED", "CHECKED_IN", "WEIGHING", "COMPLETED"];

const STATUS_META = {
  CONFIRMED:  { label: "Confirmed",  icon: "🎫", cls: "pill-confirmed" },
  CHECKED_IN: { label: "Checked In", icon: "✅", cls: "pill-checked_in" },
  WEIGHING:   { label: "Weighing",   icon: "⚖",  cls: "pill-weighing" },
  COMPLETED:  { label: "Completed",  icon: "💰", cls: "pill-completed" },
  CANCELLED:  { label: "Cancelled",  icon: "❌", cls: "pill-cancelled" },
  PENDING:    { label: "Pending",    icon: "⏳", cls: "pill-pending" },
};

function ProgressBar({ status }) {
  const stepIdx = STATUS_STEPS.indexOf(status);
  if (stepIdx < 0 || status === "CANCELLED") return null;

  return (
    <div style={{ marginTop: "0.75rem" }}>
      <div style={{ display: "flex", gap: "0", position: "relative" }}>
        {STATUS_STEPS.map((s, i) => {
          const done = i <= stepIdx;
          const active = i === stepIdx;
          return (
            <div key={s} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "0.3rem" }}>
              {/* connector line left */}
              <div style={{ display: "flex", alignItems: "center", width: "100%", position: "relative" }}>
                {i > 0 && (
                  <div style={{
                    flex: 1, height: "2px",
                    background: i <= stepIdx ? "#22d3ee" : "rgba(255,255,255,0.1)",
                    transition: "background 0.3s",
                  }} />
                )}
                <div style={{
                  width: "22px", height: "22px", borderRadius: "50%", flexShrink: 0,
                  background: done ? (active ? "#22d3ee" : "#0891b2") : "rgba(255,255,255,0.06)",
                  border: `2px solid ${done ? "#22d3ee" : "rgba(255,255,255,0.12)"}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "0.65rem", fontWeight: 700,
                  color: done ? "#fff" : "#475569",
                  transition: "all 0.3s",
                  boxShadow: active ? "0 0 10px rgba(34,211,238,0.5)" : "none",
                }}>
                  {done ? (active ? "●" : "✓") : i + 1}
                </div>
                {i < STATUS_STEPS.length - 1 && (
                  <div style={{
                    flex: 1, height: "2px",
                    background: i < stepIdx ? "#22d3ee" : "rgba(255,255,255,0.1)",
                    transition: "background 0.3s",
                  }} />
                )}
              </div>
              <div style={{ fontSize: "0.6rem", color: done ? "#94a3b8" : "#334155", textAlign: "center" }}>
                {STATUS_META[s].label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function BookingCard({ booking, highlight }) {
  const meta = STATUS_META[booking.status] || STATUS_META.PENDING;
  const isActive = ["CONFIRMED", "CHECKED_IN", "WEIGHING"].includes(booking.status);
  const MSP = 2275.0;
  const estPayout = (booking.estimated_quantity_quintals * MSP).toLocaleString("en-IN");

  return (
    <div style={{
      background: highlight
        ? "linear-gradient(135deg, rgba(34,211,238,0.06), rgba(99,102,241,0.06))"
        : "rgba(255,255,255,0.03)",
      border: `1px solid ${highlight ? "rgba(34,211,238,0.2)" : "rgba(255,255,255,0.08)"}`,
      borderRadius: "14px",
      padding: "1rem 1.1rem",
      transition: "border-color 0.2s",
    }}>
      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "1rem", fontWeight: 800, color: "#22d3ee" }}>
              Token #{booking.queue_number}
            </span>
            <span className={`pill ${meta.cls}`}>{meta.icon} {meta.label}</span>
          </div>
          <div style={{ fontSize: "0.78rem", color: "#475569", marginTop: "0.25rem", fontFamily: "monospace" }}>
            {booking.booking_reference}
          </div>
        </div>

        {/* Farmers ahead badge */}
        {isActive && (
          <div style={{
            background: booking.farmers_ahead === 0 ? "rgba(74,222,128,0.12)" : "rgba(251,191,36,0.1)",
            border: `1px solid ${booking.farmers_ahead === 0 ? "rgba(74,222,128,0.3)" : "rgba(251,191,36,0.2)"}`,
            borderRadius: "10px", padding: "0.4rem 0.75rem", textAlign: "center", flexShrink: 0,
          }}>
            <div style={{
              fontSize: "1.1rem", fontWeight: 800,
              color: booking.farmers_ahead === 0 ? "#4ade80" : "#fbbf24",
            }}>
              {booking.farmers_ahead}
            </div>
            <div style={{ fontSize: "0.6rem", color: "#64748b" }}>ahead</div>
          </div>
        )}
      </div>

      {/* Progress bar for active */}
      {isActive && <ProgressBar status={booking.status} />}

      {/* Info grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginTop: "0.85rem" }}>
        {[
          { icon: "🏛", label: booking.center_name.length > 20 ? booking.center_district : booking.center_name },
          { icon: "📅", label: booking.booking_date },
          { icon: "🌾", label: booking.crop_type },
          { icon: "⚖", label: `${booking.estimated_quantity_quintals} Quintals` },
        ].map(({ icon, label }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.8rem", color: "#64748b" }}>
            <span>{icon}</span><span>{label}</span>
          </div>
        ))}
      </div>

      {/* ETA + payout row */}
      {(booking.estimated_arrival_time || booking.status === "COMPLETED") && (
        <div style={{
          marginTop: "0.75rem", padding: "0.55rem 0.85rem",
          background: "rgba(255,255,255,0.03)", borderRadius: "8px",
          display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem",
        }}>
          {booking.estimated_arrival_time && isActive && (
            <div style={{ fontSize: "0.8rem" }}>
              <span style={{ color: "#475569" }}>ETA: </span>
              <span style={{ color: "#38bdf8", fontWeight: 600 }}>{booking.estimated_arrival_time}</span>
            </div>
          )}
          <div style={{ fontSize: "0.8rem" }}>
            <span style={{ color: "#475569" }}>Est. MSP: </span>
            <span style={{ color: "#c084fc", fontWeight: 600 }}>Rs {estPayout}</span>
          </div>
        </div>
      )}
    </div>
  );
}
