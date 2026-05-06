// Tasks page — pages/Tasks.tsx. Failed retry queue, retry/discard actions.
const { RefreshCw, Trash, Clock } = window.R115Icons;

const TASKS = [
  { id: "t-9421", kind: "fetch_post",     target: "/forum/thread/118842",  attempts: 3, last: "0.7s ago",  err: "ETIMEDOUT" },
  { id: "t-9420", kind: "post_telegram",  target: "@reaper115_alerts",     attempts: 2, last: "12s ago",   err: "Bad Gateway 502" },
  { id: "t-9419", kind: "fetch_post",     target: "/forum/thread/118822",  attempts: 5, last: "1m ago",    err: "Cloudflare 1020" },
  { id: "t-9418", kind: "extract_magnet", target: "id=118791",             attempts: 1, last: "4m ago",    err: "regex no match" },
  { id: "t-9417", kind: "fetch_post",     target: "/forum/thread/118770",  attempts: 2, last: "11m ago",   err: "ECONNRESET" },
];

function Tasks() {
  return (
    <>
      <PageHeader
        title="Tasks"
        desc="Failed jobs awaiting retry. Backoff is exponential up to 6 attempts."
        actions={<>
          <Button variant="secondary" size="sm" icon={<Trash className="icon" />}>Discard all</Button>
          <Button variant="primary" size="sm" icon={<RefreshCw className="icon" />}>Retry all</Button>
        </>}
      />

      <div className="grid-4" style={{ marginBottom: 16 }}>
        <StatCard label="Pending"  value="14" icon={<Clock className="icon" />} tone="warning" />
        <StatCard label="Failed"   value="7"  icon={<Clock className="icon" />} tone="danger" />
        <StatCard label="Retried (24h)" value="38" icon={<RefreshCw className="icon" />} tone="primary" />
        <StatCard label="Discarded (24h)" value="2" icon={<Trash className="icon" />} tone="default" />
      </div>

      <Card>
        <table>
          <thead>
            <tr>
              <th style={{ width: 100 }}>ID</th>
              <th style={{ width: 150 }}>Job</th>
              <th>Target</th>
              <th style={{ width: 90 }}>Attempts</th>
              <th style={{ width: 110 }}>Last</th>
              <th>Error</th>
              <th style={{ width: 130 }}></th>
            </tr>
          </thead>
          <tbody>
            {TASKS.map((t) => (
              <tr key={t.id}>
                <td className="mono">{t.id}</td>
                <td><Badge>{t.kind}</Badge></td>
                <td className="mono" style={{ fontSize: 12 }}>{t.target}</td>
                <td>{t.attempts}/6</td>
                <td className="sub mono">{t.last}</td>
                <td><span style={{ color: "#D8281D", fontFamily: "var(--font-mono)", fontSize: 12 }}>{t.err}</span></td>
                <td>
                  <div className="row gap-2">
                    <Button variant="secondary" size="sm" icon={<RefreshCw className="icon" />}>Retry</Button>
                    <Button variant="ghost"     size="sm" icon={<Trash className="icon" />} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

window.Tasks = Tasks;
