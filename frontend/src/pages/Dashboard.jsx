import { useState } from "react";

import CalendarView from "../components/CalendarView";
import Chat from "../components/Chat";
import TaskList from "../components/TaskList";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { user } = useAuth();
  const [refreshCounter, setRefreshCounter] = useState(0);
  const greeting = user?.name?.split(" ")[0] || "there";

  const handleTaskCreated = () => {
    setRefreshCounter((value) => value + 1);
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
        </div>
      </section>

      <section className="dashboard-grid">
        <Chat onTaskCreated={handleTaskCreated} />
        <TaskList refreshSignal={refreshCounter} />
        <CalendarView refreshSignal={refreshCounter} />
      </section>
    </main>
  );
}
