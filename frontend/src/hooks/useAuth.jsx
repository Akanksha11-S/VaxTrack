import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, setUnauthorizedHandler, tokenStore } from "../services/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(tokenStore.get()));
  const [sessionExpired, setSessionExpired] = useState(false);

  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => { tokenStore.clear(); setUser(null); setSessionExpired(true); });
  }, []);

  useEffect(() => {
    if (!tokenStore.get()) return;
    api.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const finish = useCallback((res) => { tokenStore.set(res.access_token); setUser(res.user); setSessionExpired(false); return res.user; }, []);
  const login = useCallback(async (body) => finish(await api.login(body)), [finish]);
  const register = useCallback(async (body) => finish(await api.register(body)), [finish]);

  const value = useMemo(
    () => ({ user, setUser, loading, login, register, logout, sessionExpired }),
    [user, loading, login, register, logout, sessionExpired]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
