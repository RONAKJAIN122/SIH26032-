import { useState } from "react";
import LoginPage from "./pages/LoginPage";
import FarmerDashboard from "./pages/FarmerDashboard";
import BookSlotPage from "./pages/BookSlotPage";
import "./App.css";

// Simple client-side "router" using state
// Views: "login" | "dashboard" | "book"

export default function App() {
  const [view, setView] = useState("login");
  const [farmer, setFarmer] = useState(null); // logged-in farmer object

  const handleLogin = (farmerData) => {
    setFarmer(farmerData);
    setView("dashboard");
  };

  const handleLogout = () => {
    setFarmer(null);
    setView("login");
  };

  return (
    <div className="app-root">
      {view === "login" && (
        <LoginPage onLogin={handleLogin} />
      )}
      {view === "dashboard" && farmer && (
        <FarmerDashboard
          farmer={farmer}
          onBookSlot={() => setView("book")}
          onLogout={handleLogout}
        />
      )}
      {view === "book" && farmer && (
        <BookSlotPage
          farmer={farmer}
          onBack={() => setView("dashboard")}
          onBooked={() => setView("dashboard")}
        />
      )}
    </div>
  );
}
