import { useState } from "react";

import CalendarView from "../components/CalendarView";
import Chat from "../components/Chat";
import TaskList from "../components/TaskList";
import { useAuth } from "../context/AuthContext";
import { syncCalendar } from "../api/calendarService";

export default function Dashboard() {
  const { user } = useAuth();
  const [refreshCounter, setRefreshCounter] = useState(0);
  const [syncState, setSyncState] = useState({ syncing: false, message: "" });
  const greeting = user?.name?.split(" ")[0] || "there";

  const handleTaskChanged = () => {
    setRefreshCounter((value) => value + 1);
  };

  const handleManualSync = async () => {
    setSyncState({ syncing: true, message: "Sincronizando calendario..." });
    try {
      const result = await syncCalendar();
      if (result.reason === "in_progress") {
        setSyncState({ syncing: false, message: "" });
        return;
      }
      if (result.reason === "throttled") {
        setSyncState({ syncing: false, message: "Sincronizado recientemente." });
      } else {
        setSyncState({ syncing: false, message: `✅ ${result.imported} importados, ${result.skipped} omitidos.` });
        handleTaskChanged(); // Refresh the views
      }
      
      // Clear message after 4 seconds
      setTimeout(() => setSyncState(s => ({ ...s, message: "" })), 4000);
    } catch (err) {
      setSyncState({ syncing: false, message: "❌ Error al sincronizar." });
      setTimeout(() => setSyncState(s => ({ ...s, message: "" })), 4000);
    }
  };

  return (
    <main className="dashboard-shell">
      <section className="hero-banner">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>{greeting}, your calendar is ready for conversation.</h1>
          <p>
            Use chat to schedule tasks, review what is coming up, and see everything aligned on the calendar.
          </p>
          <div style={{ marginTop: "16px", display: "flex", alignItems: "center", gap: "16px" }}>
            <button 
              className="primary-button" 
              onClick={handleManualSync} 
              disabled={syncState.syncing}
            >
              {syncState.syncing ? "Sincronizando..." : "Sync Calendar"}
            </button>
            {syncState.message && <span style={{ fontSize: "14px", color: "var(--foreground-muted)" }}>{syncState.message}</span>}
          </div>
        </div>
      </section>

      <section className="dashboard-grid">
        <Chat onTaskCreated={handleTaskChanged} />
        <TaskList onTaskDeleted={handleTaskChanged} refreshSignal={refreshCounter} />
        <CalendarView refreshSignal={refreshCounter} />
      </section>
    </main>
  );
}
