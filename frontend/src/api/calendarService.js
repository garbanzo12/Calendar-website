import apiClient from "./client";

let isSyncing = false;

export const syncCalendar = async (token = null) => {
  if (isSyncing) {
    console.warn("Sync already in progress, skipping...");
    return { imported: 0, skipped: 0, calendars: 0, reason: "in_progress" };
  }

  isSyncing = true;
  try {
    const config = token ? { headers: { Authorization: `Bearer ${token}` } } : {};
    const res = await apiClient.get("/calendar/sync", config);
    return res.data;
  } finally {
    isSyncing = false;
  }
};
