import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  Database,
  Film,
  Gauge,
  ListTodo,
  LogOut,
  RefreshCw,
  Server,
  Sliders,
} from "lucide-react";
import { systemApi } from "../api/queries";

const NAV_ITEMS = [
  { to: "/", label: "仪表盘", icon: Gauge },
  { to: "/config", label: "系统配置", icon: Server },
  { to: "/strategy", label: "抓取策略", icon: Sliders },
  { to: "/sehua", label: "涩花数据", icon: Database },
  { to: "/missav", label: "missav 数据", icon: Film },
  { to: "/tasks", label: "重试任务", icon: ListTodo },
  { to: "/crawl", label: "手动抓取", icon: Activity },
];

export function AppLayout({
  authRequired,
  onLogout,
}: {
  authRequired?: boolean;
  onLogout?: () => void;
}) {
  const statusQuery = useQuery({
    queryKey: ["system", "status"],
    queryFn: systemApi.status,
  });
  const appVersion = statusQuery.data?.appVersion;

  return (
    <div className="flex min-h-screen">
      {/* ── Sidebar ── */}
      <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-[var(--glass-border)] bg-[var(--glass-fill-sidebar)] shadow-glass backdrop-blur-[var(--glass-blur)]">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-[var(--glass-border)] px-4">
          <img
            className="h-10 w-10 rounded-lg shadow-[0_10px_22px_rgba(0,122,255,0.18)]"
            src="/brand/sehuatang-115-bot.svg"
            alt="Reaper115"
          />
          <div className="min-w-0">
            <span className="block truncate text-sm font-semibold tracking-tight text-[var(--r115-ink)]">
              Reaper115
            </span>
            <span className="block truncate text-[11px] text-primary">
              管理控制台
              {appVersion ? (
                <span className="ml-1 text-[var(--r115-slate)]">v{appVersion}</span>
              ) : null}
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex flex-1 flex-col gap-1.5 p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                isActive
                  ? "flex h-8 items-center gap-2.5 rounded-md bg-primary px-2.5 text-sm font-medium text-white shadow-[0_12px_28px_rgba(0,122,255,0.24)] transition-colors"
                  : "flex h-8 items-center gap-2.5 rounded-md px-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-white/55 hover:text-foreground"
              }
            >
              <item.icon className="h-3.5 w-3.5 shrink-0" />
              <span className="min-w-0 truncate">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-[var(--glass-border)] p-3 font-mono text-[11px] text-muted-foreground opacity-65">
          v0.4.2 · staging
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar */}
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-[var(--glass-border)] bg-white/50 px-6 backdrop-blur-[var(--glass-blur)]">
          <div className="min-w-0 flex-1">
            <PageTitle />
          </div>
          <button
            className="icon-btn inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-white/55 hover:text-foreground"
            aria-label="刷新"
            onClick={() => window.location.reload()}
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            className="icon-btn inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-white/55 hover:text-foreground"
            aria-label="通知"
          >
            <Bell className="h-4 w-4" />
          </button>
          {authRequired ? (
            <button
              className="icon-btn inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-white/55 hover:text-foreground"
              aria-label="退出登录"
              onClick={onLogout}
            >
              <LogOut className="h-4 w-4" />
            </button>
          ) : null}
        </header>

        <main className="mx-auto w-full max-w-[1152px] px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function PageTitle() {
  return <div className="text-sm font-semibold text-foreground">Reaper115</div>;
}
