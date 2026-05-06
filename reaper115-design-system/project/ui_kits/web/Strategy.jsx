// Strategy / config page — pages/Config.tsx + Strategy.tsx folded together.
// Crawl cadence form on top, sections grid, then keyword rules table + regex tester.
const { Save, Plus, Trash, Pencil, Play } = window.R115Icons;

const SECTIONS = [
  { id: "new",   name: "新作品",     enabled: true,  pages: 5, depth: 2 },
  { id: "asia",  name: "亚洲无码",   enabled: true,  pages: 3, depth: 2 },
  { id: "eu",    name: "欧美",       enabled: true,  pages: 3, depth: 1 },
  { id: "other", name: "其它",       enabled: false, pages: 1, depth: 1 },
];
const RULES = [
  { id: 1, kind: "include", pattern: "(SSIS|SONE|MIDV)-\\d{3,4}", section: "新作品",   active: true },
  { id: 2, kind: "include", pattern: "FC2-PPV-\\d{4,5}",         section: "亚洲无码",  active: true },
  { id: 3, kind: "exclude", pattern: "trailer|preview|sample",     section: "*",         active: true },
  { id: 4, kind: "include", pattern: "\\b(8K|VR|passthrough)\\b",  section: "欧美",      active: false },
];

function Strategy() {
  const [sections, setSections] = React.useState(SECTIONS);
  return (
    <>
      <PageHeader
        title="Strategy"
        desc="Tune the crawler — cadence, sections, keyword rules. Saved to crawler.yaml."
        actions={<Button variant="primary" size="sm" icon={<Save className="icon" />}>Save changes</Button>}
      />

      <div className="grid-2-eq" style={{ marginBottom: 16 }}>
        <Card>
          <h2>Cadence</h2>
          <div className="col gap-3">
            <Field label="Schedule">
              <Select defaultValue="hourly">
                <option value="cron">Cron (custom)</option>
                <option value="hourly">Every hour</option>
                <option value="6h">Every 6 hours</option>
                <option value="daily">Daily 04:00 UTC</option>
              </Select>
            </Field>
            <div className="grid-2-eq">
              <Field label="Concurrency"><Input defaultValue="4" /></Field>
              <Field label="Request delay (ms)"><Input defaultValue="800" /></Field>
            </div>
            <Field label="User-Agent">
              <Input defaultValue="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) Reaper/0.4" />
            </Field>
            <div className="row between">
              <span className="muted" style={{ fontSize: 13 }}>Honor robots.txt</span>
              <Switch on={true} />
            </div>
            <div className="row between">
              <span className="muted" style={{ fontSize: 13 }}>Use proxy pool</span>
              <Switch on={false} />
            </div>
          </div>
        </Card>

        <Card>
          <div className="row between" style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>Sections</h2>
            <Button variant="secondary" size="sm" icon={<Plus className="icon" />}>Add</Button>
          </div>
          <div className="col">
            {sections.map((s, i) => (
              <div key={s.id} className="inset-row">
                <div>
                  <div style={{ fontWeight: 500 }}>{s.name}</div>
                  <div className="muted" style={{ fontSize: 12 }}>{s.pages} pages · depth {s.depth}</div>
                </div>
                <Switch on={s.enabled} onChange={(v) => {
                  const next = [...sections]; next[i] = { ...s, enabled: v }; setSections(next);
                }} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div className="row between" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Keyword rules</h2>
          <Button variant="secondary" size="sm" icon={<Plus className="icon" />}>New rule</Button>
        </div>
        <table>
          <thead>
            <tr>
              <th style={{ width: 40 }}>#</th>
              <th style={{ width: 100 }}>Type</th>
              <th>Pattern</th>
              <th style={{ width: 130 }}>Section</th>
              <th style={{ width: 80 }}>Active</th>
              <th style={{ width: 90 }}></th>
            </tr>
          </thead>
          <tbody>
            {RULES.map((r) => (
              <tr key={r.id}>
                <td className="mono muted">{r.id}</td>
                <td>{r.kind === "include"
                    ? <Badge tone="success">include</Badge>
                    : <Badge tone="danger">exclude</Badge>}</td>
                <td><span className="mono" style={{ fontSize: 13 }}>{r.pattern}</span></td>
                <td>{r.section}</td>
                <td><Switch on={r.active} /></td>
                <td>
                  <div className="row gap-2">
                    <Button variant="ghost" size="sm" icon={<Pencil className="icon" />} />
                    <Button variant="ghost" size="sm" icon={<Trash className="icon" />} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card>
        <h2>Regex tester</h2>
        <div className="grid-2-eq">
          <Field label="Pattern">
            <Input defaultValue="(SSIS|SONE|MIDV)-\\d{3,4}" />
          </Field>
          <Field label="Test string">
            <Input defaultValue="[新作品][SSIS-985] 蓝色彼岸 完全主観" />
          </Field>
        </div>
        <div className="row gap-2" style={{ marginTop: 12 }}>
          <Button variant="primary" size="sm" icon={<Play className="icon" />}>Run</Button>
          <Badge tone="success">1 match · SSIS-985</Badge>
        </div>
      </Card>
    </>
  );
}

window.Strategy = Strategy;
