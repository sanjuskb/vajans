/**
 * VAJANS — Axios API Client
 * Central HTTP client with request/response interceptors,
 * error normalisation, and request-ID tracking.
 */

import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ── Request interceptor ─────────────────────────────────────────────────────
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem("vajans_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor ────────────────────────────────────────────────────
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<{ message?: string; error?: string }>) => {
    // If 401, clear auth state and redirect to login
    if (error.response?.status === 401) {
      localStorage.removeItem("vajans_token");
      localStorage.removeItem("vajans_username");
      localStorage.removeItem("vajans_role");
      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }

    const message =
      error.response?.data?.message ??
      error.response?.data?.error ??
      error.message ??
      "An unexpected error occurred";

    const normalised = {
      status: error.response?.status ?? 0,
      message,
      requestId: error.response?.headers?.["x-request-id"],
      raw: error,
    };

    console.error("[VAJANS API Error]", normalised);
    return Promise.reject(normalised);
  }
);

export default apiClient;
