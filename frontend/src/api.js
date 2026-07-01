import axios from "axios";
import { appBase, appPath } from "./appBase";

const api = axios.create({ baseURL: appPath("/api") });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem("token");
      if (!location.pathname.startsWith(appPath("/login"))) location.href = appPath("/login");
    }
    return Promise.reject(err);
  }
);

export default api;
