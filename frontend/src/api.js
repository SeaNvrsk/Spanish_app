import axios from "axios";
import { appBase, appPath } from "./appBase";

const api = axios.create({ baseURL: appPath("/api") });

api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } catch {
    /* Safari storage blocked */
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      try {
        localStorage.removeItem("token");
      } catch {
        /* ignore */
      }
      if (!location.pathname.startsWith(appPath("/login"))) location.href = appPath("/login");
    }
    return Promise.reject(err);
  }
);

export default api;
