import { NavLink, Outlet } from "react-router-dom";
import { Activity, Bot, Database, Gauge, Menu, ScrollText, ServerCog, Settings2, Sliders, X } from "lucide-react";

import { API_BASE_URL } from "../api/client";
import { cn } from "../lib/utils";
import { useUiStore } from "../store/ui";
import { Button } from "./ui";

const navItems = [
  { to: "/", label: "Dashboard", icon: Gauge },
  { to: "/sehua", label: "涩花数据", icon: Database },
  { to: "/strategy", label: "策略管理", icon: Settings2 },
  { to: "/tasks", label: "离线任务", icon: ScrollText },
  { to: "/crawl", label: "爬取控制", icon: Activity },
  { to: "/config", label: "配置管理", icon: Sliders },
  { to: "/system", label: "系统状态", icon: ServerCog },
];

export function AppLayout() {
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-64 border-r border-border bg-surface transition-transform lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-border px-4">
          <div className="flex items-center gap-2 font-semibold">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Bot className="h-5 w-5" />
            </span>
            Sehua Web
          </div>
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="关闭导航">
            <X className="h-5 w-5" />
          </Button>
        </div>
        <nav className="space-y-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  isActive && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground",
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 border-t border-border p-4 text-xs text-muted-foreground">
          API: <span className="break-all font-mono">{API_BASE_URL}</span>
        </div>
      </aside>
      {sidebarOpen ? <button className="fixed inset-0 z-30 bg-black/25 lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="关闭遮罩" /> : null}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-surface/95 px-4 backdrop-blur">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)} aria-label="打开导航">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="text-sm text-muted-foreground">Telegram-115bot 管理界面</div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 md:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
