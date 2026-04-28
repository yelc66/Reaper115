import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { Config } from "./pages/Config";
import { Crawl } from "./pages/Crawl";
import { Dashboard } from "./pages/Dashboard";
import { NotFound } from "./pages/NotFound";
import { SehuaData } from "./pages/SehuaData";
import { Strategy } from "./pages/Strategy";
import { System } from "./pages/System";
import { Tasks } from "./pages/Tasks";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sehua" element={<SehuaData />} />
        <Route path="/strategy" element={<Strategy />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/crawl" element={<Crawl />} />
        <Route path="/config" element={<Config />} />
        <Route path="/system" element={<System />} />
        <Route path="/dashboard" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
