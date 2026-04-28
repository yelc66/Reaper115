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
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-56 flex-col border-r border-border bg-surface transition-transform lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Logo */}
        <div className="flex h-12 items-center gap-2.5 border-b border-border px-4">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-primary">
            <Bot className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Sehua Web</span>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-6 w-6 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="关闭导航"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 p-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex h-8 items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors",
                  isActive
                    ? "bg-primary/12 text-primary font-medium"
                    : "text-muted-foreground hover:bg-surface-elevated hover:text-foreground",
                )
              }
            >
              <item.icon className="h-3.5 w-3.5 shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-border p-3 text-xs text-muted-foreground">
          <div className="truncate font-mono opacity-60">{API_BASE_URL}</div>
        </div>
      </aside>

      {/* Overlay */}
      {sidebarOpen ? (
        <button
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="关闭遮罩"
        />
      ) : null}

      {/* Main */}
      <div className="lg:pl-56">
        <header className="sticky top-0 z-20 flex h-12 items-center gap-3 border-b border-border bg-surface/80 px-4 backdrop-blur">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="打开导航"
          >
            <Menu className="h-4 w-4" />
          </Button>
          <div className="text-xs text-muted-foreground">Telegram-115bot 管理界面</div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-5 md:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
