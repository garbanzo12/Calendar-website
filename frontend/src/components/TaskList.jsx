import { useEffect, useState } from "react";

import apiClient from "../api/client";

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function TaskList({ refreshSignal }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTasks = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await apiClient.get("/tasks");
      setTasks(response.data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to load tasks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [refreshSignal]);

  const handleDelete = async (taskId) => {
    try {
      await apiClient.delete(`/tasks/${taskId}`);
      setTasks((current) => current.filter((task) => task.id !== taskId));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to delete task.");
    }
  };

  return (
    <section className="panel task-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Tasks</p>
          <h2>Upcoming list</h2>
        </div>
        <button className="ghost-button" onClick={loadTasks} type="button">
          Refresh
        </button>
      </div>

      {loading ? <p className="status-text">Loading tasks...</p> : null}
      {error ? <p className="status-text error-text">{error}</p> : null}

      <div className="task-list">
        {!loading && tasks.length === 0 ? <p className="status-text">No tasks yet.</p> : null}

        {tasks.map((task) => (
          <article className="task-card" key={task.id}>
            <div>
              <h3>{task.title}</h3>
              <p>{task.description || "No description"}</p>
              <span>{formatDate(task.date)}</span>
            </div>
            <button className="danger-button" onClick={() => handleDelete(task.id)} type="button">
              Delete
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
