import { useState } from "react";

const API = "http://127.0.0.1:8000";

const DISTRICTS = [
  "Ambala", "Hisar", "Karnal", "Kurukshetra", "Ludhiana",
  "Patiala", "Rohtak", "Sirsa", "Sonipat", "Yamunanagar",
  "Amritsar", "Bathinda", "Fatehgarh Sahib", "Gurdaspur", "Hoshiarpur",
];

export default function LoginPage({ onLogin }) {
  const [phase, setPhase] = useState("phone");   // "phone" | "otp" | "register"
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [foundFarmer, setFoundFarmer] = useState(null);

  // Registration form state
  const [regForm, setRegForm] = useState({
    name: "", village: "", district: "Karnal", state: "Haryana",
    has_linked_bank_account: false, bank_account_number: "", ifsc_code: "",
  });

  // ── Step 1: Phone lookup ─────────────────────────────────────
  const handlePhoneLookup = async (e) => {
    e.preventDefault();
    const clean = phone.replace(/\D/g, "");
    if (clean.length !== 10) {
      setError("Please enter a valid 10-digit phone number.");
      return;
    }
    setError(""); setLoading(true);
    try {
      const res = await fetch(`${API}/api/farmers/by-phone/${clean}`);
      if (res.ok) {
        const farmer = await res.json();
        setFoundFarmer(farmer);
        setPhase("otp");   // found → show dummy OTP screen
      } else if (res.status === 404) {
        setPhase("register");  // not found → registration
      } else {
        setError("Server error. Please try again.");
      }
    } catch {
      setError("Cannot connect to server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2: Dummy OTP verify ─────────────────────────────────
  const handleOtpVerify = (e) => {
    e.preventDefault();
    if (otp.length < 4) { setError("Enter the OTP sent to your phone."); return; }
    // Dummy: any OTP works — this is KYC simulation
    setError("");
    onLogin(foundFarmer);
  };

  // ── Step 2b: New farmer registration ─────────────────────────
  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regForm.name.trim()) { setError("Please enter your full name."); return; }
    setError(""); setLoading(true);
    const clean = phone.replace(/\D/g, "");
    try {
      const res = await fetch(`${API}/api/farmers/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...regForm,
          phone_number: clean,
          bank_account_number: regForm.has_linked_bank_account ? regForm.bank_account_number : null,
          ifsc_code: regForm.has_linked_bank_account ? regForm.ifsc_code : null,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        onLogin(data);
      } else {
        setError(data.detail || "Registration failed.");
      }
    } catch {
      setError("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>

      {/* Hero */}
      <div style={{ textAlign: "center", marginBottom: "2rem", paddingTop: "2rem" }}>
        <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>🌾</div>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#f1f5f9", letterSpacing: "-0.02em" }}>
          SmartMandi
        </h1>
        <p style={{ color: "#64748b", fontSize: "0.9rem", marginTop: "0.3rem" }}>
          Smart Grain Queue Manager · SIH26032
        </p>
      </div>

      {/* ── PHASE: phone ──────────────────────────────────── */}
      {phase === "phone" && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div>
            <h2 style={{ fontSize: "1.2rem", fontWeight: 700 }}>Farmer Login</h2>
            <p style={{ color: "#64748b", fontSize: "0.88rem", marginTop: "0.25rem" }}>
              Enter your registered mobile number to continue
            </p>
          </div>

          <form onSubmit={handlePhoneLookup} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div className="input-group">
              <label className="input-label">Mobile Number</label>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <span style={{
                  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.10)",
                  borderRadius: "10px", padding: "0.75rem 0.85rem",
                  color: "#94a3b8", fontSize: "0.95rem", whiteSpace: "nowrap"
                }}>🇮🇳 +91</span>
                <input
                  className="input-field"
                  type="tel"
                  placeholder="9876543210"
                  maxLength={10}
                  value={phone}
                  onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
                  style={{ flex: 1 }}
                  required
                />
              </div>
            </div>

            {error && <div className="error-msg">{error}</div>}

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : "Get OTP →"}
            </button>
          </form>

          <div style={{ textAlign: "center", color: "#475569", fontSize: "0.82rem" }}>
            New farmer? Enter your phone and we'll guide you to register.
          </div>
        </div>
      )}

      {/* ── PHASE: otp ────────────────────────────────────── */}
      {phase === "otp" && foundFarmer && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <button className="btn btn-ghost" style={{ alignSelf: "flex-start", padding: 0 }}
            onClick={() => { setPhase("phone"); setError(""); setOtp(""); }}>
            ← Back
          </button>

          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>📱</div>
            <h2 style={{ fontSize: "1.2rem", fontWeight: 700 }}>OTP Verification</h2>
            <p style={{ color: "#64748b", fontSize: "0.88rem", marginTop: "0.3rem" }}>
              OTP sent to +91-{phone.slice(0, 5)}XXXXX
            </p>
            <div style={{
              marginTop: "0.75rem", padding: "0.6rem 1rem",
              background: "rgba(34,211,238,0.08)", border: "1px solid rgba(34,211,238,0.2)",
              borderRadius: "10px", color: "#22d3ee", fontSize: "0.85rem",
            }}>
              Welcome back, <strong>{foundFarmer.name}</strong> 👋
            </div>
          </div>

          <form onSubmit={handleOtpVerify} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div className="input-group">
              <label className="input-label">Enter OTP</label>
              <input
                className="input-field"
                type="tel"
                placeholder="_ _ _ _ _ _"
                maxLength={6}
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                style={{ fontSize: "1.5rem", letterSpacing: "0.4em", textAlign: "center" }}
                autoFocus
              />
            </div>
            <p style={{ color: "#475569", fontSize: "0.78rem", textAlign: "center" }}>
              Demo: any 4+ digit code works
            </p>
            {error && <div className="error-msg">{error}</div>}
            <button type="submit" className="btn btn-primary">Verify & Login</button>
          </form>
        </div>
      )}

      {/* ── PHASE: register ───────────────────────────────── */}
      {phase === "register" && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <button className="btn btn-ghost" style={{ alignSelf: "flex-start", padding: 0 }}
            onClick={() => { setPhase("phone"); setError(""); }}>
            ← Back
          </button>

          <div>
            <h2 style={{ fontSize: "1.2rem", fontWeight: 700 }}>New Farmer Registration</h2>
            <p style={{ color: "#64748b", fontSize: "0.85rem", marginTop: "0.25rem" }}>
              Phone +91-{phone} not found. Fill details to register.
            </p>
          </div>

          <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
            <div className="input-group">
              <label className="input-label">Full Name *</label>
              <input className="input-field" placeholder="Gurpreet Singh"
                value={regForm.name}
                onChange={e => setRegForm(p => ({ ...p, name: e.target.value }))} required />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div className="input-group">
                <label className="input-label">Village</label>
                <input className="input-field" placeholder="Taraori"
                  value={regForm.village}
                  onChange={e => setRegForm(p => ({ ...p, village: e.target.value }))} />
              </div>
              <div className="input-group">
                <label className="input-label">District *</label>
                <select className="input-field"
                  value={regForm.district}
                  onChange={e => setRegForm(p => ({ ...p, district: e.target.value }))}>
                  {DISTRICTS.map(d => <option key={d}>{d}</option>)}
                </select>
              </div>
            </div>

            <div className="input-group">
              <label className="input-label">State *</label>
              <select className="input-field"
                value={regForm.state}
                onChange={e => setRegForm(p => ({ ...p, state: e.target.value }))}>
                <option>Haryana</option>
                <option>Punjab</option>
              </select>
            </div>

            {/* Bank linked toggle */}
            <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", padding: "0.9rem 1rem" }}>
              <div className="toggle-row">
                <span className="toggle-label">🏦 Linked Bank Account (for MSP payment)</span>
                <label className="toggle-switch">
                  <input type="checkbox"
                    checked={regForm.has_linked_bank_account}
                    onChange={e => setRegForm(p => ({ ...p, has_linked_bank_account: e.target.checked }))} />
                  <span className="toggle-track" />
                  <span className="toggle-thumb" />
                </label>
              </div>

              {regForm.has_linked_bank_account && (
                <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.65rem" }}>
                  <div className="input-group">
                    <label className="input-label">Account Number</label>
                    <input className="input-field" placeholder="123456789012"
                      value={regForm.bank_account_number}
                      onChange={e => setRegForm(p => ({ ...p, bank_account_number: e.target.value }))} />
                  </div>
                  <div className="input-group">
                    <label className="input-label">IFSC Code</label>
                    <input className="input-field" placeholder="SBIN0001234"
                      value={regForm.ifsc_code}
                      onChange={e => setRegForm(p => ({ ...p, ifsc_code: e.target.value.toUpperCase() }))} />
                  </div>
                </div>
              )}
            </div>

            {error && <div className="error-msg">{error}</div>}
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : "Register & Enter →"}
            </button>
          </form>
        </div>
      )}

      <p style={{ textAlign: "center", color: "#334155", fontSize: "0.75rem", marginTop: "2rem" }}>
        Smart India Hackathon 2026 · SIH26032
      </p>
    </div>
  );
}
