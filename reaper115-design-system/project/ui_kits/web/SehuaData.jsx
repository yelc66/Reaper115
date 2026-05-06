// Sehua data table — pages/SehuaData.tsx. Filter row + paginated rows.
const { Search, Filter, FileText, ChevronLeft, ChevronRight } = window.R115Icons;

const SEHUA = Array.from({ length: 8 }).map((_, i) => ({
  id: 38_421 - i,
  title: ["[新作品][SSIS-985] 蓝色彼岸 完全主観",
          "[亚洲无码] 4K 60fps remux",
          "[欧美] [SLR] VR 8K passthrough",
          "[新作品][PRED-721] 制服 篇 — disc 2",
          "[亚洲无码] FC2-PPV-4421-002",
          "[新作品] 限定特典 BD 1080p",
          "[欧美] [Brazzers] 2025-05-04",
          "[其它] 自拍 流出 mixed"][i % 8],
  size: ["4.21 GB","12.40 GB","18.02 GB","6.88 GB","2.13 GB","9.44 GB","3.02 GB","1.74 GB"][i % 8],
  posted: `2025-05-${String(6 - (i % 5)).padStart(2,"0")} 0${(i%9)+1}:1${i%6}`,
  status: ["ok","ok","ok","warn","ok","ok","ok","fail"][i % 8],
}));

function SehuaData() {
  return (
    <>
      <PageHeader
        title="Sehua data"
        desc="Posts ingested from the crawler. Filter, audit, batch-export to magnets."
        actions={<>
          <Button variant="secondary" size="sm" icon={<Filter className="icon" />}>Filter</Button>
          <Button variant="primary" size="sm" icon={<FileText className="icon" />}>Export selected</Button>
        </>}
      />

      <Card className="row gap-3" style={{ flexWrap: "wrap", marginBottom: 16, padding: 12 }}>
        <div style={{ position: "relative", flex: "1 1 320px" }}>
          <Search className="icon" style={{ position: "absolute", left: 12, top: 9, color: "hsl(var(--muted-foreground))" }} />
          <input className="input" placeholder="Search title, code, magnet…" style={{ paddingLeft: 34 }} />
        </div>
        <Select style={{ width: 160 }} defaultValue="all">
          <option value="all">All sections</option>
          <option>新作品</option>
          <option>亚洲无码</option>
          <option>欧美</option>
          <option>其它</option>
        </Select>
        <Select style={{ width: 130 }} defaultValue="any">
          <option value="any">Any status</option>
          <option>ok</option>
          <option>partial</option>
          <option>failed</option>
        </Select>
        <Input type="date" style={{ width: 150 }} defaultValue="2025-05-04" />
      </Card>

      <Card>
        <table>
          <thead>
            <tr>
              <th style={{ width: 32 }}><input type="checkbox" /></th>
              <th style={{ width: 90 }}>ID</th>
              <th>Title</th>
              <th style={{ width: 110 }}>Size</th>
              <th style={{ width: 150 }}>Posted</th>
              <th style={{ width: 100 }}>Status</th>
              <th style={{ width: 60 }}></th>
            </tr>
          </thead>
          <tbody>
            {SEHUA.map((r) => (
              <tr key={r.id}>
                <td><input type="checkbox" defaultChecked={r.id % 3 === 0} /></td>
                <td className="mono">#{r.id}</td>
                <td>
                  <div className="cell-title">{r.title}</div>
                  <div className="cell-sub">magnet:?xt=urn:btih:7c4a8d09ca37…{r.id % 1000}</div>
                </td>
                <td className="mono">{r.size}</td>
                <td className="sub mono">{r.posted}</td>
                <td>
                  {r.status === "ok"   && <Badge tone="success">ok</Badge>}
                  {r.status === "warn" && <Badge tone="warning">partial</Badge>}
                  {r.status === "fail" && <Badge tone="danger">failed</Badge>}
                </td>
                <td><Button variant="ghost" size="sm">Open</Button></td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="row between" style={{ marginTop: 12 }}>
          <span className="muted" style={{ fontSize: 12 }}>Showing 1–8 of 1,184</span>
          <div className="row gap-2">
            <Button variant="ghost" size="sm" icon={<ChevronLeft className="icon" />} />
            <Button variant="secondary" size="sm">1</Button>
            <Button variant="ghost" size="sm">2</Button>
            <Button variant="ghost" size="sm">3</Button>
            <Button variant="ghost" size="sm">…</Button>
            <Button variant="ghost" size="sm">148</Button>
            <Button variant="ghost" size="sm" icon={<ChevronRight className="icon" />} />
          </div>
        </div>
      </Card>
    </>
  );
}

window.SehuaData = SehuaData;
