import { useState } from "react";

import CalendarView from "../components/CalendarView";
import Chat from "../components/Chat";
import TaskList from "../components/TaskList";
import { useAuth } from "../context/AuthContext";

export default function Dashboard({ isDarkTheme, onToggleTheme }) {
  const { user } = useAuth();
  const [refreshCounter, setRefreshCounter] = useState(0);
  const greeting = user?.name?.split(" ")[0] || "there";

  const handleTaskChanged = () => {
    setRefreshCounter((value) => value + 1);
  };

  return (
    <main className="dashboard-shell">
      <section className="hero-banner">
        <div className="hero-content">
          <p className="eyebrow">Dashboard</p>
          <h1>{greeting}, your calendar is ready for conversation.</h1>
          <p>
            Use chat to schedule tasks, review what is coming up, and see everything aligned on the calendar.
          </p>
        </div>
        <button className="ghost-button dashboard-theme-toggle" onClick={onToggleTheme} type="button">
          {isDarkTheme ? "Light mode" : "Dark mode"}
        </button>
      </section>

      <section className="dashboard-grid">
        <Chat onTaskCreated={handleTaskChanged} />
        <TaskList onTaskDeleted={handleTaskChanged} refreshSignal={refreshCounter} />
        <CalendarView refreshSignal={refreshCounter} />
      </section>
    </main>
  );
}
