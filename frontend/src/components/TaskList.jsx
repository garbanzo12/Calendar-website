import { useEffect, useState } from "react";

import apiClient from "../api/client";

const TASKS_PER_PAGE = 4;

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

/** Convert a Date or ISO string to a value accepted by datetime-local inputs */
function toDatetimeLocal(value) {
  if (!value) return "";
  const d = new Date(value);
  if (isNaN(d)) return "";
  // Format: YYYY-MM-DDTHH:mm
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

export default function TaskList({ onTaskDeleted, refreshSignal }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ── Pagination ──────────────────────────────────────────────
  const [currentPage, setCurrentPage] = useState(1);
  const tasksPerPage = TASKS_PER_PAGE;

  const totalPages = Math.max(1, Math.ceil(tasks.length / tasksPerPage));
  const indexOfLastTask = currentPage * tasksPerPage;
  const indexOfFirstTask = indexOfLastTask - tasksPerPage;
  const currentTasks = tasks.slice(indexOfFirstTask, indexOfLastTask);

  // ── Edit state ───────────────────────────────────────────────
  const [editingTask, setEditingTask] = useState(null);
  const [formData, setFormData] = useState({ title: "", description: "", date: "" });
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState("");

  // ── Load ─────────────────────────────────────────────────────
  const loadTasks = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await apiClient.get("/tasks");
      setTasks(response.data);
      setCurrentPage(1); // reset to page 1 on every refresh
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to load tasks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [refreshSignal]);

  // ── Delete ────────────────────────────────────────────────────
  const handleDelete = async (taskId) => {
    try {
      await apiClient.delete(`/tasks/${taskId}`);
      setTasks((current) => {
        const updated = current.filter((task) => task.id !== taskId);
        // If we deleted the last item on the current page, go back one page
        const newTotalPages = Math.max(1, Math.ceil(updated.length / tasksPerPage));
        if (currentPage > newTotalPages) setCurrentPage(newTotalPages);
        return updated;
      });
      setError("");

      if (onTaskDeleted) {
        onTaskDeleted(taskId);
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to delete task.");
    }
  };

  // ── Open edit modal ───────────────────────────────────────────
  const handleEditOpen = (task) => {
    setEditingTask(task);
    setEditError("");
    setFormData({
      title: task.title || "",
      description: task.description || "",
      date: toDatetimeLocal(task.date),
    });
  };

  const handleEditClose = () => {
    setEditingTask(null);
    setEditError("");
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // ── Submit edit ───────────────────────────────────────────────
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setEditError("");

    try {
      const payload = {
        title: formData.title,
        description: formData.description || null,
        date: formData.date ? new Date(formData.date).toISOString() : null,
      };

      const response = await apiClient.put(`/tasks/${editingTask.id}`, payload);
      const updated = response.data;

      setTasks((current) =>
        current.map((t) => (t.id === updated.id ? updated : t))
      );
      handleEditClose();
    } catch (requestError) {
      console.error("Failed to update task:", requestError);
      setEditError(requestError.response?.data?.detail || "Unable to save changes.");
    } finally {
      setSaving(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────
  return (
    <>
      {/* ── Edit Modal ─────────────────────────────────────────── */}
      {editingTask && (
        <div className="modal-overlay" onClick={handleEditClose}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Edit Task</h3>
              <button
                className="modal-close"
                onClick={handleEditClose}
                type="button"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <form className="edit-form" onSubmit={handleEditSubmit}>
              <label>
                <span>Title</span>
                <input
                  type="text"
                  name="title"
                  value={formData.title}
                  onChange={handleFormChange}
                  required
                  placeholder="Task title"
                />
              </label>

              <label>
                <span>Description</span>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleFormChange}
                  rows={3}
                  placeholder="Optional description"
                />
              </label>

              <label>
                <span>Date &amp; Time</span>
                <input
                  type="datetime-local"
                  name="date"
                  value={formData.date}
                  onChange={handleFormChange}
                  required
                />
              </label>

              {editError && <p className="status-text error-text">{editError}</p>}

              <div className="modal-actions">
                <button
                  className="ghost-button"
                  type="button"
                  onClick={handleEditClose}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button className="primary-button" type="submit" disabled={saving}>
                  {saving ? "Saving…" : "Save changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Task panel ─────────────────────────────────────────── */}
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

        {loading ? <p className="status-text">Loading tasks…</p> : null}
        {error ? <p className="status-text error-text">{error}</p> : null}

        <div className="task-list">
          {!loading && tasks.length === 0 ? (
            <p className="status-text">No tasks yet.</p>
          ) : null}

          {currentTasks.map((task) => (
            <article className="task-card" key={task.id}>
              <div className="task-card-info">
                <h3>{task.title}</h3>
                <p>{task.description || "No description"}</p>
                <span>{formatDate(task.date)}</span>
              </div>
              <div className="task-card-actions">
                <button
                  className="edit-button"
                  onClick={() => handleEditOpen(task)}
                  type="button"
                >
                  Edit
                </button>
                <button
                  className="danger-button"
                  onClick={() => handleDelete(task.id)}
                  type="button"
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>

        {/* ── Pagination ──────────────────────────────────────── */}
        {tasks.length > tasksPerPage && (
          <div className="pagination">
            <button
              className="page-btn"
              onClick={() => setCurrentPage((p) => p - 1)}
              disabled={currentPage === 1}
              type="button"
            >
              ← Prev
            </button>

            <span className="page-info">
              Page {currentPage} of {totalPages}
            </span>

            <button
              className="page-btn"
              onClick={() => setCurrentPage((p) => p + 1)}
              disabled={currentPage === totalPages}
              type="button"
            >
              Next →
            </button>
          </div>
        )}
      </section>
    </>
  );
}
