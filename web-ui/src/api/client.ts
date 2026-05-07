import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
export const WEB_AUTH_KEY_STORAGE = "web_auth_key";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export function getStoredAuthKey() {
  return localStorage.getItem(WEB_AUTH_KEY_STORAGE) || "";
}

export function setStoredAuthKey(key: string) {
  localStorage.setItem(WEB_AUTH_KEY_STORAGE, key);
}

export function clearStoredAuthKey() {
  localStorage.removeItem(WEB_AUTH_KEY_STORAGE);
}

api.interceptors.request.use((config) => {
  const authKey = getStoredAuthKey();
  if (authKey) {
    config.headers.set("x-web-auth-key", authKey);
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearStoredAuthKey();
      window.dispatchEvent(new Event("web-auth:unauthorized"));
    }

    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return Promise.reject(new Error(detail));
    }
    return Promise.reject(error);
  },
);
