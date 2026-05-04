import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL?.trim();

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("calendar_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API] ${response.config.method.toUpperCase()} ${response.config.url} → ${response.status}`);
    return response;
  },
  (error) => {
    const config = error.config;
    const method = config?.method?.toUpperCase() || "UNKNOWN";
    const url = config?.url || "UNKNOWN";
    const status = error.response?.status || error.code || "UNKNOWN";
    const message = error.response?.data?.detail || error.response?.data || error.message;

    if (!API_BASE_URL) {
      error.userMessage = "API base URL is not configured. Set VITE_API_URL to your deployed FastAPI backend.";
    } else if (!error.response) {
      error.userMessage = "Unable to reach the backend right now. Please try again in a moment.";
    }

    if (status === 401) {
      localStorage.removeItem("calendar_token");
      localStorage.removeItem("calendar_user");
      window.location.href = "/login";
    }

    console.error(`[ERROR] ${method} ${url} → ${status}`, message);
    return Promise.reject(error);
  }
);

export default apiClient;
