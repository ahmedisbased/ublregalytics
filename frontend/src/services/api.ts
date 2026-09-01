import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/').replace(/\/?$/, '/');

const api = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    "Content-Type": "application/json",
  },
});


// Attach the short-lived access token to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Clear session and bounce to login.
function forceLogout() {
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

// On a 401, transparently try ONE refresh using the refresh token, then retry
// the original request. This is what lets access tokens be short-lived without
// logging the user out every 30 minutes.
let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh_token = localStorage.getItem("refresh_token");
  if (!refresh_token) return null;
  try {
    const { data } = await axios.post(
      `${apiBaseUrl}refresh`,
      { refresh_token },
      { headers: { "Content-Type": "application/json" } }
    );
    if (data?.access_token) {
      localStorage.setItem("token", data.access_token);
      return data.access_token as string;
    }
    return null;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean };
    const status = error.response?.status;
    const url = original?.url ?? "";

    const isAuthEndpoint = url.includes("login") || url.includes("refresh");

    if (status === 401 && original && !original._retried && !isAuthEndpoint) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken();
      const newToken = await refreshing;
      refreshing = null;

      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
      forceLogout();
    }

    return Promise.reject(error);
  }
);

export default api;
