import { NavLink, Outlet } from "react-router-dom";
import {
  Activity,
  Database,
  Gauge,
  LogOut,
  Menu,
  Moon,
  ScrollText,
  Settings2,
  Sliders,
  Sun,
  X,
} from "lucide-react";

import { API_BASE_URL } from "../api/client";
import { cn } from "../lib/utils";
import { useUiStore } from "../store/ui";
import { Button } from "./ui";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: Gauge },
  { to: "/config", label: "配置管理", icon: Sliders },
  { to: "/strategy", label: "爬虫配置", icon: Settings2 },
  { to: "/sehua", label: "涩花数据", icon: Database },
  { to: "/tasks", label: "离线任务", icon: ScrollText },
  { to: "/crawl", label: "爬取控制", icon: Activity },
];

export function AppLayout({ authRequired, onLogout }: { authRequired?: boolean; onLogout?: () => void }) {
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);
  const theme = useUiStore((state) => state.theme);
  const toggleTheme = useUiStore((state) => state.toggleTheme);

  return (
    <div className="min-h-screen text-foreground">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-white/60 bg-white/58 shadow-glass backdrop-blur-2xl transition-transform dark:border-white/10 dark:bg-white/10 lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-white/60 px-4 dark:border-white/10">
          <img
            className="h-10 w-10 rounded-lg shadow-[0_10px_22px_rgba(0,122,255,0.18)]"
            src="/brand/sehuatang-115-bot.svg"
            alt="Reaper115"
          />
          <div className="min-w-0">
            <span className="block truncate text-sm font-semibold tracking-tight">Reaper115</span>
            <span className="block truncate text-xs text-primary">Telegram 管理控制台</span>
          </div>
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
        <nav className="flex-1 space-y-1.5 p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex h-8 items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground font-medium shadow-[0_12px_28px_rgba(0,122,255,0.24)]"
                    : "text-muted-foreground hover:bg-white/54 hover:text-foreground dark:hover:bg-white/10",
                )
              }
            >
              <item.icon className="h-3.5 w-3.5 shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-white/60 p-3 text-xs text-muted-foreground dark:border-white/10">
          <div className="truncate font-mono opacity-60">{API_BASE_URL}</div>
        </div>
      </aside>

      {/* Overlay */}
      {sidebarOpen ? (
        <button
          className="fixed inset-0 z-30 bg-slate-950/30 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="关闭遮罩"
        />
      ) : null}

      {/* Main */}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-white/60 bg-white/50 px-4 backdrop-blur-2xl dark:border-white/10 dark:bg-slate-950/40">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="打开导航"
          >
            <Menu className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">Reaper115</div>
            <div className="truncate text-xs text-muted-foreground">Telegram-115bot 管理界面</div>
          </div>
          {authRequired ? (
            <Button
              variant="ghost"
              size="icon"
              className="ml-auto h-7 w-7"
              onClick={onLogout}
              aria-label="退出登录"
              title="退出登录"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          ) : null}
          <Button
            variant="ghost"
            size="icon"
            className={cn("h-7 w-7", authRequired ? "" : "ml-auto")}
            onClick={toggleTheme}
            aria-label="切换主题"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 md:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
