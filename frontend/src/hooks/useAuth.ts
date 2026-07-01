import { useState, useCallback } from "react";
import { login as apiLogin, logout as apiLogout } from "../services/auth";

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem("access_token"));

  const login = useCallback(async (username: string, password: string) => {
    await apiLogin(username, password);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setIsAuthenticated(false);
  }, []);

  return { isAuthenticated, login, logout };
}
