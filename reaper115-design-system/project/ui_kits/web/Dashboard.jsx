// Dashboard: status panel + 4 stat cards + 30-day trend (placeholder line chart) +
// section donut + recent crawls table. Layout follows pages/Dashboard.tsx.
const { Activity, Cpu, HardDrive, Wifi, Server, Database: DB,
        FileText, ListTodo, Check, Clock, RefreshCw } = window.R115Icons;

function StatusRow({ icon, label, value, tone = "success" }) {
  return (
    <div className="inset-row" style={{ marginBottom: 6 }}>
      <div className="row gap-2" style={{ color: "hsl(var(--muted-foreground))", fontSize: 13 }}>
        {icon}<span>{label}</span>
      </div>
      <Badge tone={tone}>{value}</Badge>
    </div>
  );
}

function FakeLine() {
  // simple hand-drawn-ish polyline; values represent crawled posts/day
  const pts = [12, 28, 22, 41, 35, 52, 47, 68, 58, 74, 66, 81, 72, 90, 85, 96, 88, 102, 110, 99, 118, 124, 116, 132, 140, 128, 146, 152, 144, 158];
  const maxY = Math.max(...pts);
  const w = 520, h = 200, pad = 12;
  const stepX = (w - pad * 2) / (pts.length - 1);
  const path = pts.map((y, i) => `${i === 0 ? "M" : "L"} ${pad + i * stepX} ${h - pad - (y / maxY) * (h - pad * 2)}`).join(" ");
  const area = `${path} L ${w - pad} ${h - pad} L ${pad} ${h - pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="lf" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="rgba(0,122,255,0.28)" />
          <stop offset="100%" stopColor="rgba(0,122,255,0)" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#lf)" />
      <path d={path} fill="none" stroke="var(--r115-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FakeDonut() {
  // donut for section share — values match table below
  const segs = [
    { v: 42, color: "#007AFF", label: "新作品" },
    { v: 24, color: "#34C759", label: "亚洲无码" },
    { v: 18, color: "#FF9500", label: "欧美" },
    { v: 16, color: "#AF52DE", label: "其它" },
  ];
  const total = segs.reduce((a, s) => a + s.v, 0);
  const C = 2 * Math.PI * 38;
  let offset = 0;
  return (
    <div className="row gap-4" style={{ width: "100%", justifyContent: "center" }}>
      <svg width="140" height="140" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="38" fill="none" stroke="rgba(28,28,30,0.06)" strokeWidth="14" />
        {segs.map((s, i) => {
          const len = (s.v / total) * C;
          const el = (
            <circle key={i} cx="50" cy="50" r="38" fill="none"
              stroke={s.color} strokeWidth="14"
              strokeDasharray={`${len} ${C - len}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 50 50)"
            />
          );
          offset += len;
          return el;
        })}
        <text x="50" y="48" textAnchor="middle" fontSize="14" fontWeight="600" fill="#1C1C1E" fontFamily="var(--font-sans)">418</text>
        <text x="50" y="62" textAnchor="middle" fontSize="7" fill="#8E8E93" fontFamily="var(--font-sans)">7-day total</text>
      </svg>
      <div className="donut-legend">
        {segs.map((s) => (
          <div className="legend-row" key={s.label}>
            <span className="legend-dot" style={{ background: s.color }}></span>
            <span style={{ color: "var(--r115-ink)" }}>{s.label}</span>
            <span style={{ marginLeft: "auto" }}>{Math.round((s.v / total) * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const RECENT = [
  { id: 11942, section: "新作品",     status: "ok",   posts: 38, ts: "10:42:11" },
  { id: 11941, section: "亚洲无码",   status: "ok",   posts: 22, ts: "10:08:50" },
  { id: 11940, section: "欧美",       status: "warn", posts: 14, ts: "09:21:33" },
  { id: 11939, section: "其它",       status: "ok",   posts: 19, ts: "08:54:02" },
  { id: 11938, section: "新作品",     status: "fail", posts: 0,  ts: "08:11:47" },
];

function Dashboard() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        desc="System health, crawl throughput, recent activity."
        actions={<>
          <Button variant="secondary" size="sm" icon={<RefreshCw className="icon" />}>Refresh</Button>
          <Button variant="primary" size="sm">Run crawl</Button>
        </>}
      />

      <div className="grid-status" style={{ marginBottom: 16 }}>
        <Card>
          <h2>System</h2>
          <StatusRow icon={<Server className="icon" />}    label="API" value="Online" tone="success" />
          <StatusRow icon={<DB className="icon" />}        label="Database" value="Online" tone="success" />
          <StatusRow icon={<Wifi className="icon" />}      label="Telegram" value="Connected" tone="success" />
          <StatusRow icon={<Cpu className="icon" />}       label="CPU" value="32%" tone="info" />
          <StatusRow icon={<HardDrive className="icon" />} label="Disk" value="68%" tone="warning" />
        </Card>

        <div className="col">
          <div className="grid-2-eq">
            <StatCard label="Crawled today"    value="2,418" icon={<Activity className="icon" />} tone="primary" />
            <StatCard label="Magnets queued"   value="312"   icon={<ListTodo className="icon" />} tone="warning" />
            <StatCard label="Sehua matched"    value="1,184" icon={<DB className="icon" />}      tone="success" />
            <StatCard label="Failed retries"   value="7"     icon={<FileText className="icon" />} tone="danger" />
          </div>
        </div>
      </div>

      <div className="grid-2-1" style={{ marginBottom: 16 }}>
        <Card>
          <div className="row between" style={{ marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>30-day crawl volume</h2>
            <Badge tone="info">posts/day</Badge>
          </div>
          <div className="chart-shell"><FakeLine /></div>
        </Card>
        <Card>
          <div className="row between" style={{ marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>Section share</h2>
            <Badge>7d</Badge>
          </div>
          <div className="chart-shell fake-donut"><FakeDonut /></div>
        </Card>
      </div>

      <Card>
        <div className="row between" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Recent crawls</h2>
          <Button variant="ghost" size="sm">View all →</Button>
        </div>
        <table>
          <thead>
            <tr>
              <th style={{ width: 90 }}>ID</th>
              <th>Section</th>
              <th style={{ width: 100 }}>Status</th>
              <th style={{ width: 100 }}>Posts</th>
              <th style={{ width: 120 }}>Time</th>
            </tr>
          </thead>
          <tbody>
            {RECENT.map((r) => (
              <tr key={r.id}>
                <td className="mono">#{r.id}</td>
                <td>{r.section}</td>
                <td>
                  {r.status === "ok"   && <Badge tone="success"><Check className="icon" style={{ width: 10, height: 10 }} /> ok</Badge>}
                  {r.status === "warn" && <Badge tone="warning">partial</Badge>}
                  {r.status === "fail" && <Badge tone="danger">failed</Badge>}
                </td>
                <td>{r.posts}</td>
                <td className="sub mono">{r.ts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

window.Dashboard = Dashboard;
