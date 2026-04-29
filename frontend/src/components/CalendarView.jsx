import { useEffect, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";

import apiClient from "../api/client";
import { getApiErrorMessage } from "../api/errors";

export default function CalendarView({ refreshSignal }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadEvents = async () => {
      setLoading(true);
      setError("");

      try {
        const response = await apiClient.get("/tasks");
        const mappedEvents = response.data.map((task) => ({
          id: String(task.id),
          title: task.title,
          start: task.date,
          allDay: false,
        }));
        setEvents(mappedEvents);
      } catch (requestError) {
        setError(getApiErrorMessage(requestError, "Unable to load calendar."));
      } finally {
        setLoading(false);
      }
    };

    loadEvents();
  }, [refreshSignal]);

  return (
    <section className="panel calendar-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Calendar</p>
          <h2>Date view</h2>
        </div>
      </div>

      {error ? <p className="status-text error-text">{error}</p> : null}
      {loading ? <p className="status-text">Loading calendar...</p> : null}

      <div className="calendar-wrapper">
        <FullCalendar
          plugins={[dayGridPlugin, interactionPlugin]}
          headerToolbar={{
            left: "prev,next today",
            center: "title",
            right: "dayGridMonth,dayGridWeek",
          }}
          events={events}
          height="auto"
        />
      </div>
    </section>
  );
}
