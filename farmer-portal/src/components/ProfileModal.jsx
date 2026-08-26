export default function ProfileModal({ farmer, bookings, onClose, onLogout }) {
  const initials = farmer.name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const MSP = 2275.0;
  const totalCompleted = bookings.filter((b) => b.status === "COMPLETED").length;
  const totalActive = bookings.filter((b) =>
    ["CONFIRMED", "CHECKED_IN", "WEIGHING"].includes(b.status)
  ).length;
  const totalPayout = bookings
    .filter((b) => b.status === "COMPLETED")
    .reduce((s, b) => s + b.estimated_quantity_quintals * MSP, 0);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div className="profile-large-avatar">{initials}</div>
            <div>
              <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: 0 }}>
                {farmer.name}
              </h3>
              <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", margin: 0 }}>
                Farmer ID #{farmer.id}
              </p>
            </div>
          </div>
          <button className="btn-icon-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {/* KYC Badge */}
        <div className="kyc-badge-row">
          <span className="kyc-pill">
            <span style={{ fontSize: "0.85rem" }}>✓</span> Verified Farmer KYC
          </span>
          <span
            style={{
              fontSize: "0.75rem",
              padding: "0.2rem 0.6rem",
              borderRadius: "9999px",
              background: farmer.has_linked_bank_account
                ? "rgba(74,222,128,0.15)"
                : "rgba(251,191,36,0.15)",
              color: farmer.has_linked_bank_account ? "#4ade80" : "#fbbf24",
              border: `1px solid ${
                farmer.has_linked_bank_account
                  ? "rgba(74,222,128,0.3)"
                  : "rgba(251,191,36,0.3)"
              }`,
            }}
          >
            {farmer.has_linked_bank_account ? "Direct MSP Deposit" : "No Bank Linked"}
          </span>
        </div>

        {/* Details Grid */}
        <div className="profile-info-section">
          <div className="profile-info-row">
            <span className="info-label">📞 Mobile Number</span>
            <span className="info-val font-mono">+91-{farmer.phone_number}</span>
          </div>
          <div className="profile-info-row">
            <span className="info-label">📍 Farm Location</span>
            <span className="info-val">
              {farmer.village ? `${farmer.village}, ` : ""}
              {farmer.district}, {farmer.state}
            </span>
          </div>
          {farmer.has_linked_bank_account && (
            <>
              <div className="profile-info-row">
                <span className="info-label">🏦 Bank Account</span>
                <span className="info-val font-mono">
                  {farmer.bank_account_number
                    ? `•••• •••• ${farmer.bank_account_number.slice(-4)}`
                    : "Linked via Aadhaar"}
                </span>
              </div>
              {farmer.ifsc_code && (
                <div className="profile-info-row">
                  <span className="info-label">🏛 IFSC Code</span>
                  <span className="info-val font-mono">{farmer.ifsc_code}</span>
                </div>
              )}
            </>
          )}
        </div>

        {/* Stats Grid */}
        <div className="profile-stats-grid">
          <div className="profile-stat-box">
            <span className="stat-value-sm" style={{ color: "#22d3ee" }}>
              {totalActive}
            </span>
            <span className="stat-label-sm">Active Slots</span>
          </div>
          <div className="profile-stat-box">
            <span className="stat-value-sm" style={{ color: "#4ade80" }}>
              {totalCompleted}
            </span>
            <span className="stat-label-sm">Delivered</span>
          </div>
          <div className="profile-stat-box">
            <span className="stat-value-sm" style={{ color: "#c084fc" }}>
              {totalPayout > 0 ? `₹${(totalPayout / 1000).toFixed(0)}k` : "₹0"}
            </span>
            <span className="stat-label-sm">MSP Payout</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginTop: "1.25rem" }}>
          <button className="btn btn-secondary" onClick={onClose}>
            Back to Dashboard
          </button>
          <button
            className="btn btn-logout"
            onClick={() => {
              onClose();
              onLogout();
            }}
          >
            🚪 Logout from Account
          </button>
        </div>
      </div>
    </div>
  );
}
