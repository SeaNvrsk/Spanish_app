import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "./api";
import { useI18n, normalizeUiLang } from "./i18n";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const { setLang } = useI18n();

  const refresh = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      if (data.ui_language) setLang(normalizeUiLang(data.ui_language));
      return data;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, [setLang]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login-json", { email, password });
    localStorage.setItem("token", data.access_token);
    return refresh();
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    localStorage.setItem("token", data.access_token);
    return refresh();
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  const updateUser = (partial) => setUser((u) => ({ ...u, ...partial }));

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
