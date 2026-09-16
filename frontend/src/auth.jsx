import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "./api";
import { useI18n, normalizeUiLang } from "./i18n";

const AuthContext = createContext(null);

function readToken() {
  try {
    return localStorage.getItem("token");
  } catch {
    return null;
  }
}

function writeToken(token) {
  try {
    localStorage.setItem("token", token);
  } catch {
    /* Safari private / blocked storage */
  }
}

function clearToken() {
  try {
    localStorage.removeItem("token");
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const { setLang } = useI18n();

  const markReady = useCallback(() => {
    try {
      document.documentElement.setAttribute("data-espanol-ready", "1");
    } catch {
      /* ignore */
    }
  }, []);

  const refresh = useCallback(async () => {
    const token = readToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      markReady();
      return null;
    }
    try {
      const { data } = await api.get("/auth/me", { timeout: 8000 });
      setUser(data);
      if (data.ui_language) setLang(normalizeUiLang(data.ui_language));
      return data;
    } catch {
      clearToken();
      setUser(null);
      return null;
    } finally {
      setLoading(false);
      markReady();
    }
  }, [setLang, markReady]);

  useEffect(() => {
    let cancelled = false;
    const failSafe = setTimeout(() => {
      if (!cancelled) {
        setLoading(false);
        markReady();
      }
    }, 9000);
    refresh().finally(() => clearTimeout(failSafe));
    return () => {
      cancelled = true;
      clearTimeout(failSafe);
    };
  }, [refresh]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login-json", { email, password }, { timeout: 15000 });
    writeToken(data.access_token);
    return refresh();
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload, { timeout: 15000 });
    writeToken(data.access_token);
    return refresh();
  };

  const logout = () => {
    clearToken();
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
