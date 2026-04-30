import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { clearStoredAuthKey, getStoredAuthKey, setStoredAuthKey } from "./api/client";
import { authApi } from "./api/queries";
import { AppLayout } from "./components/AppLayout";
import { LoadingState } from "./components/ui";
import { Config } from "./pages/Config";
import { Crawl } from "./pages/Crawl";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { NotFound } from "./pages/NotFound";
import { SehuaData } from "./pages/SehuaData";
import { Strategy } from "./pages/Strategy";
import { Tasks } from "./pages/Tasks";

export function App() {
  const [authRequired, setAuthRequired] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

  const logout = useCallback(() => {
    clearStoredAuthKey();
    setAuthenticated(false);
  }, []);

  const login = useCallback((key: string) => {
    setStoredAuthKey(key);
    setAuthenticated(true);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function checkAuth() {
      try {
        const status = await authApi.status();
        if (cancelled) {
          return;
        }

        setAuthRequired(status.auth_required);
        if (!status.auth_required) {
          setAuthenticated(true);
          return;
        }

        const storedKey = getStoredAuthKey();
        if (!storedKey) {
          setAuthenticated(false);
          return;
        }

        await authApi.login(storedKey);
        if (!cancelled) {
          setAuthenticated(true);
        }
      } catch {
        if (!cancelled) {
          clearStoredAuthKey();
          setAuthenticated(false);
        }
      } finally {
        if (!cancelled) {
          setCheckingAuth(false);
        }
      }
    }

    checkAuth();
    window.addEventListener("web-auth:unauthorized", logout);
    return () => {
      cancelled = true;
      window.removeEventListener("web-auth:unauthorized", logout);
    };
  }, [logout]);

  if (checkingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center text-foreground">
        <LoadingState />
      </div>
    );
  }

  if (authRequired && !authenticated) {
    return <Login onLogin={login} />;
  }

  return (
    <Routes>
      <Route element={<AppLayout authRequired={authRequired} onLogout={logout} />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sehua" element={<SehuaData />} />
        <Route path="/strategy" element={<Strategy />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/crawl" element={<Crawl />} />
        <Route path="/config" element={<Config />} />
        <Route path="/system" element={<Navigate to="/" replace />} />
        <Route path="/dashboard" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
