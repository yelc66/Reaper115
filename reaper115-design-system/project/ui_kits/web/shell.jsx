// AppShell: sidebar + topbar + page slot. Mirrors components/AppLayout.tsx.
// Nav state is local — clicking switches the active page in index.html.
const { Gauge, Sliders, Database, ListTodo, Spider, Bell, RefreshCw, LogOut, Server } = window.R115Icons;

const NAV = [
  { id: "dashboard", label: "Dashboard",   icon: <Gauge className="icon" /> },
  { id: "strategy",  label: "Strategy",    icon: <Sliders className="icon" /> },
  { id: "sehua",     label: "Sehua data",  icon: <Database className="icon" /> },
  { id: "tasks",     label: "Tasks",       icon: <ListTodo className="icon" /> },
  { id: "crawl",     label: "Crawl",       icon: <Spider className="icon" /> },
  { id: "config",    label: "Config",      icon: <Server className="icon" /> },
];

function Sidebar({ active, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img src="../../assets/logo/sehuatang-115-bot-256.png" alt="Reaper115" />
        <div className="sidebar-brand">
          <span className="name">Reaper115</span>
          <span className="sub">Console</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        {NAV.map((n) => (
          <button
            key={n.id}
            className={cx("nav-item", n.id === active && "active")}
            onClick={() => onNavigate(n.id)}
          >
            {n.icon}<span>{n.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">v0.4.2 · staging</div>
    </aside>
  );
}

function TopBar({ title, sub, right }) {
  return (
    <div className="topbar">
      <div>
        <div className="title">{title}</div>
        {sub && <div className="sub">{sub}</div>}
      </div>
      <div className="grow"></div>
      {right || (
        <>
          <button className="icon-btn" aria-label="Refresh"><RefreshCw className="icon" /></button>
          <button className="icon-btn" aria-label="Notifications"><Bell className="icon" /></button>
          <button className="icon-btn" aria-label="Sign out"><LogOut className="icon" /></button>
        </>
      )}
    </div>
  );
}

function AppShell({ active, onNavigate, title, sub, children }) {
  return (
    <div className="app">
      <Sidebar active={active} onNavigate={onNavigate} />
      <main className="main">
        <TopBar title={title} sub={sub} />
        <div className="page">{children}</div>
      </main>
    </div>
  );
}

Object.assign(window, { AppShell, Sidebar, TopBar, NAV });
