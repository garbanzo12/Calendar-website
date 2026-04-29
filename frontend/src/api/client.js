import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "https://calendar-website-7vtk.onrender.com";

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
    console.error(`[ERROR] ${method} ${url} → ${status}`, message);
    return Promise.reject(error);
  }
);

export default apiClient;
