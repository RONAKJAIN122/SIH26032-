import { useState, useEffect, useRef, useCallback } from "react";
import "./Dashboard.css";

const API_BASE = "http://127.0.0.1:8000";
const WS_URL = "ws://127.0.0.1:8000/ws/dashboard";

// Status badge config
const STATUS_CONFIG = {
  PENDING:    { label: "Pending",    color: "status-pending",    next: "CONFIRMED",   action: "Confirm" },
  CONFIRMED:  { label: "Confirmed",  color: "status-confirmed",  next: "CHECKED_IN",  action: "Check In" },
  CHECKED_IN: { label: "Checked In", color: "status-checkedin",  next: "WEIGHING",    action: "Start Weighing" },
  WEIGHING:   { label: "Weighing",   color: "status-weighing",   next: "COMPLETED",   action: "Complete & Pay" },
  COMPLETED:  { label: "Completed",  color: "status-completed",  next: null,          action: null },
  CANCELLED:  { label: "Cancelled",  color: "status-cancelled",  next: null,          action: null },
};

// Individual table row with action button
function QueueRow({ item, onStatusChange, isLoading }) {
  const cfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.PENDING;

  return (
    <tr className={`queue-row ${item.status === "COMPLETED" ? "row-done" : ""}`}>
      <td>
        <span className="token-badge">#{item.queue_number}</span>
      </td>
      <td>
        <div className="farmer-cell">
          <span className="farmer-name">{item.farmer_name}</span>
          <span className="farmer-phone">{item.farmer_phone}</span>
        </div>
      </td>
      <td>
        <div className="crop-cell">
          <span className="crop-name">{item.crop_type}</span>
          <span className="crop-qty">{item.estimated_quantity_quintals} Q</span>
        </div>
      </td>
      <td>
        <span className="eta-badge">{item.dynamic_eta}</span>
      </td>
      <td>
        <span className={`status-pill ${cfg.color}`}>{cfg.label}</span>
      </td>
      <td>
        {cfg.next ? (
          <button
            className={`action-btn action-${cfg.next.toLowerCase().replace("_", "-")}`}
            onClick={() => onStatusChange(item.booking_id, cfg.next)}
            disabled={isLoading === item.booking_id}
          >
            {isLoading === item.booking_id ? "..." : cfg.action}
          </button>
        ) : (
          <button
            className="action-btn action-cancel"
            onClick={() => onStatusChange(item.booking_id, "CANCELLED")}
            disabled={isLoading === item.booking_id || item.status === "CANCELLED" || item.status === "COMPLETED"}
          >
            {item.status === "COMPLETED" ? "Paid ✓" : item.status === "CANCELLED" ? "Cancelled" : "Cancel"}
          </button>
        )}
      </td>
    </tr>
  );
}

export default function Dashboard() {
  const [queueMap, setQueueMap] = useState({});  // { [center_id]: payload }
  const [wsStatus, setWsStatus] = useState("Connecting...");
  const [loadingId, setLoadingId] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedCenter, setSelectedCenter] = useState(1);
  const [centers, setCenters] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  // Fetch available centers for the tab switcher
  useEffect(() => {
    fetch(`${API_BASE}/centers`)
      .then((r) => r.json())
      .then(setCenters)
      .catch(() => {});
  }, []);

  // Establish WebSocket connection
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus("Live");
      // Send a keepalive ping every 25s
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("PING");
        else clearInterval(ping);
      }, 25000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "QUEUE_UPDATE") {
          // Store per center_id so tab switching works correctly
          setQueueMap((prev) => ({ ...prev, [data.center_id]: data }));
          setLastUpdated(new Date());
        }
      } catch (e) {
        console.warn("[WS] Non-JSON message:", event.data);
      }
    };

    ws.onclose = () => {
      setWsStatus("Reconnecting...");
      // Auto-reconnect after 3 seconds
      reconnectTimer.current = setTimeout(connectWS, 3000);
    };

    ws.onerror = () => {
      setWsStatus("Error");
    };
  }, []);

  useEffect(() => {
    connectWS();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connectWS]);

  // Admin action: transition farmer status via REST API → triggers WS broadcast
  const handleStatusChange = async (bookingId, newStatus) => {
    setLoadingId(bookingId);
    try {
      const res = await fetch(`${API_BASE}/api/bookings/${bookingId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // The backend will automatically broadcast updated queue via WebSocket
    } catch (err) {
      console.error("Status update failed:", err);
      alert(`Failed to update status: ${err.message}`);
    } finally {
      setLoadingId(null);
    }
  };

  // When center tab changes, immediately REST-fetch that center's live queue
  // (WS pushes only on status changes — this ensures instant tab switch data)
  useEffect(() => {
    if (!selectedCenter) return;
    const today = new Date().toISOString().split("T")[0];
    fetch(`${API_BASE}/api/centers/${selectedCenter}/live-queue?target_date=${today}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data) return;
        // Convert live-queue response to the same QUEUE_UPDATE shape
        const payload = {
          event: "QUEUE_UPDATE",
          center_id: data.center_id,
          center_name: data.center_name,
          date: String(data.date),
          summary: {
            daily_capacity_quintals: data.daily_capacity_quintals,
            booked_capacity_quintals: data.booked_capacity_quintals,
            active_in_queue: data.active_in_queue_count,
            completed_today: data.completed_today_count,
            cancelled_today: 0,
            total_bookings: data.queue.length,
          },
          queue: data.queue.map((q) => ({
            booking_id: q.booking_id,
            booking_reference: q.booking_reference,
            queue_number: q.queue_number,
            farmer_id: q.farmer_id,
            farmer_name: q.farmer_name,
            farmer_phone: q.farmer_phone,
            crop_type: q.crop_type,
            estimated_quantity_quintals: q.estimated_quantity_quintals,
            status: q.status,
            dynamic_eta: q.dynamic_eta,
            farmers_ahead: q.farmers_ahead,
          })),
        };
        setQueueMap((prev) => ({ ...prev, [selectedCenter]: payload }));
        setLastUpdated(new Date());
      })
      .catch(() => {});
  }, [selectedCenter]);

  // Current center's data
  const queueData = queueMap[selectedCenter] || null;

  // Filter queue by selected center (now always correct since keyed by center_id)
  const activeQueue = queueData ? queueData.queue : [];

  const summary = queueData?.summary || {};

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dash-header">
        <div className="dash-title">
          <h1>SmartMandi Admin Dashboard</h1>
          <p className="dash-subtitle">Real-time Grain Procurement Queue Monitor</p>
        </div>
        <div className="dash-meta">
          <span className={`ws-badge ${wsStatus === "Live" ? "ws-live" : "ws-error"}`}>
            <span className="ws-dot"></span>
            {wsStatus}
          </span>
          {lastUpdated && (
            <span className="last-updated">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <span className="sih-badge">SIH26032</span>
        </div>
      </header>

      {/* Center Tabs */}
      {centers.length > 0 && (
        <nav className="center-tabs">
          {centers.map((c) => (
            <button
              key={c.id}
              className={`center-tab ${selectedCenter === c.id ? "active" : ""}`}
              onClick={() => setSelectedCenter(c.id)}
            >
              {c.district} Mandi
            </button>
          ))}
        </nav>
      )}

      {/* Summary Stats */}
      <div className="stats-row">
        <div className="stat-box">
          <span className="stat-num">{summary.active_in_queue ?? "—"}</span>
          <span className="stat-lbl">Active in Queue</span>
        </div>
        <div className="stat-box">
          <span className="stat-num">{summary.completed_today ?? "—"}</span>
          <span className="stat-lbl">Completed Today</span>
        </div>
        <div className="stat-box">
          <span className="stat-num">{summary.booked_capacity_quintals ?? "—"}</span>
          <span className="stat-lbl">Booked (Quintals)</span>
        </div>
        <div className="stat-box stat-capacity">
          <span className="stat-num">{summary.daily_capacity_quintals ?? "—"}</span>
          <span className="stat-lbl">Daily Capacity (Q)</span>
        </div>
      </div>

      {/* Queue Table */}
      <div className="table-card">
        <div className="table-header">
          <h2>
            {queueData ? `Live Queue — ${queueData.center_name} (${queueData.date})` : "Loading live queue..."}
          </h2>
          <span className="queue-count">{activeQueue.length} tokens</span>
        </div>

        {activeQueue.length === 0 ? (
          <div className="empty-state">
            <p>No active tokens for today. Refresh or wait for farmers to book slots.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="queue-table">
              <thead>
                <tr>
                  <th>Token #</th>
                  <th>Farmer</th>
                  <th>Crop / Qty</th>
                  <th>Dynamic ETA</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {activeQueue.map((item) => (
                  <QueueRow
                    key={item.booking_id}
                    item={item}
                    onStatusChange={handleStatusChange}
                    isLoading={loadingId}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <footer className="dash-footer">
        Smart India Hackathon 2026 • Project SIH26032 • SmartMandi Queue Manager
      </footer>
    </div>
  );
}
