// Crawl page — pages/Crawl.tsx. Date presets, run/stop, live SSE log pane.
const { Play, Square, Calendar } = window.R115Icons;

const LOG = [
  ["10:42:11", "info",  "Crawl started · 4 sections · concurrency 4"],
  ["10:42:11", "info",  "GET /forum/section/new?p=1 200 · 3.2KB · 412ms"],
  ["10:42:12", "info",  "matched (SSIS|SONE|MIDV)-\\d{3,4} · SSIS-985"],
  ["10:42:12", "info",  "extract_magnet ok · id=118842"],
  ["10:42:12", "info",  "GET /forum/section/asia-uncensored?p=1 200 · 2.9KB · 380ms"],
  ["10:42:13", "warn",  "rate limit hint · backing off 1.2s"],
  ["10:42:14", "info",  "GET /forum/section/eu?p=1 200 · 2.1KB · 510ms"],
  ["10:42:15", "error", "fetch_post id=118822 failed · Cloudflare 1020 · enqueueing retry 2/6"],
  ["10:42:16", "info",  "post_telegram @reaper115_alerts · ok"],
  ["10:42:17", "info",  "section new · 38 posts · 22 magnets"],
  ["10:42:18", "info",  "section asia-uncensored · 22 posts · 14 magnets"],
  ["10:42:19", "info",  "section eu · 14 posts · 9 magnets"],
  ["10:42:20", "info",  "Crawl finished · 74 posts · 45 magnets · 9.1s"],
];

function Crawl() {
  const [running, setRunning] = React.useState(false);
  const [preset, setPreset] = React.useState("today");
  const presets = [
    { id: "today",     label: "Today" },
    { id: "yesterday", label: "Yesterday" },
    { id: "7d",        label: "Last 7 days" },
    { id: "30d",       label: "Last 30 days" },
    { id: "custom",    label: "Custom…" },
  ];
  return (
    <>
      <PageHeader
        title="Crawl"
        desc="Run an ad-hoc crawl. Date range applies to source-side post.created."
        actions={running
          ? <Button variant="danger"  size="sm" icon={<Square className="icon" />} onClick={() => setRunning(false)}>Stop</Button>
          : <Button variant="primary" size="sm" icon={<Play   className="icon" />} onClick={() => setRunning(true)}>Run crawl</Button>}
      />

      <Card style={{ marginBottom: 16 }}>
        <div className="row gap-2" style={{ flexWrap: "wrap" }}>
          {presets.map((p) => (
            <button
              key={p.id}
              className={cx("btn", "sm", preset === p.id ? "primary" : "secondary")}
              onClick={() => setPreset(p.id)}
            >
              {p.label}
            </button>
          ))}
        </div>
        {preset === "custom" && (
          <div className="row gap-3" style={{ marginTop: 12 }}>
            <Field label="From"><Input type="date" defaultValue="2025-05-01" /></Field>
            <Field label="To"><Input   type="date" defaultValue="2025-05-04" /></Field>
          </div>
        )}
      </Card>

      <Card>
        <div className="row between" style={{ marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Live log</h2>
          {running
            ? <Badge tone="info">streaming · SSE</Badge>
            : <Badge>idle</Badge>}
        </div>
        <div className="log-pane">
          {LOG.map(([t, lvl, msg], i) => (
            <div key={i} className="log-line">
              <span className="log-time">{t}</span>
              <span className={`log-${lvl}`}>{lvl.toUpperCase().padEnd(5)}</span>
              <span>{msg}</span>
            </div>
          ))}
          {running && <div className="log-line"><span className="log-time">10:42:21</span><span className="log-info">INFO </span><span>cursor blinks_</span></div>}
          {!running && <div className="log-empty" style={{ marginTop: 8 }}>— stream paused —</div>}
        </div>
      </Card>
    </>
  );
}

window.Crawl = Crawl;
