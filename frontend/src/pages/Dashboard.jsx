import { useState } from "react";

import CalendarView from "../components/CalendarView";
import Chat from "../components/Chat";
import TaskList from "../components/TaskList";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { user } = useAuth();
  const [refreshCounter, setRefreshCounter] = useState(0);
  const greeting = user?.name?.split(" ")[0] || "there";

  const handleTaskChanged = () => {
    setRefreshCounter((value) => value + 1);
  };

<<<<<<< HEAD
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
      setSyncState({ syncing: false, message: getApiErrorMessage(err, "Unable to sync calendar.") });
      setTimeout(() => setSyncState(s => ({ ...s, message: "" })), 4000);
    }
  };

=======
>>>>>>> parent of 4a8ac17 (Merge pull request #8 from garbanzo12/latency-2)
  return (
    <main className="dashboard-shell">
      <section className="hero-banner">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>{greeting}, your calendar is ready for conversation.</h1>
          <p>
            Use chat to schedule tasks, review what is coming up, and see everything aligned on the calendar.
          </p>
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
