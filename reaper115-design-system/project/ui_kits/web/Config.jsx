// Config page — system / app configuration. Mirrors pages/Config.tsx:
// 基础设置 · Telegram Bot · 115 开放平台 · AI 模型. Each section saves independently.
const { Save, RefreshCw, Lock } = window.R115Icons;

function Section({ title, hint, saved, children, onSave, label = "Save" }) {
  return (
    <Card style={{ marginBottom: 16 }}>
      <div className="row between" style={{ alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0 }}>{title}</h2>
          {hint && <p className="muted" style={{ fontSize: 12, marginTop: 4, maxWidth: 460 }}>{hint}</p>}
        </div>
        {onSave && (
          <Button variant="primary" size="sm" icon={<Save className="icon" />} onClick={onSave}>
            {saved ? "Saved ✓" : label}
          </Button>
        )}
      </div>
      <div className="config-rows">{children}</div>
    </Card>
  );
}

function Row({ label, hint, children }) {
  return (
    <div className="config-row">
      <div className="config-row-label">
        <div style={{ fontSize: 14, fontWeight: 500 }}>{label}</div>
        {hint && <div className="muted" style={{ fontSize: 12, marginTop: 4, lineHeight: 1.4 }}>{hint}</div>}
      </div>
      <div className="config-row-control">{children}</div>
    </div>
  );
}

function Config() {
  const [form, setForm] = React.useState({
    logLevel: "info",
    webEnabled: true,
    webPort: "8000",
    webAuthKey: "",
    cleanEnabled: true,
    cleanLessThan: "400M",
    botToken: "",
    allowedUser: "5821094412",
    appId: "100195123",
    accessToken: "",
    refreshToken: "",
    aiApiUrl: "https://api.siliconflow.cn/v1",
    aiApiKey: "",
    aiModel: "deepseek-ai/DeepSeek-V3.2",
  });
  const [saved, setSaved] = React.useState({});
  const patch = (k, v) => setForm((p) => ({ ...p, [k]: v }));
  const save = (id) => {
    setSaved((p) => ({ ...p, [id]: true }));
    setTimeout(() => setSaved((p) => ({ ...p, [id]: false })), 2000);
  };

  return (
    <>
      <PageHeader
        title="Config"
        desc="Manage runtime configuration. Saves apply immediately (port changes need a restart)."
      />

      <Section title="Basic" onSave={() => save("basic")} saved={saved.basic}>
        <Row label="Log level">
          <Select value={form.logLevel} onChange={(e) => patch("logLevel", e.target.value)} style={{ maxWidth: 160 }}>
            {["debug", "info", "warning", "error", "critical"].map((l) => <option key={l}>{l}</option>)}
          </Select>
        </Row>
        <Row label="Web port" hint="Restart required to take effect">
          <Input type="number" value={form.webPort} onChange={(e) => patch("webPort", e.target.value)} style={{ maxWidth: 120 }} />
        </Row>
        <Row label="Enable Web UI">
          <Switch on={form.webEnabled} onChange={(v) => patch("webEnabled", v)} />
        </Row>
        <Row label="Web auth key" hint="Empty disables auth. WEB_AUTH_KEY env var takes precedence.">
          <Input type="password" value={form.webAuthKey} onChange={(e) => patch("webAuthKey", e.target.value)} placeholder="leave empty to disable" />
        </Row>
        <Row label="Ad-cleanup" hint="Auto-delete files smaller than threshold as ads">
          <Switch on={form.cleanEnabled} onChange={(v) => patch("cleanEnabled", v)} />
        </Row>
        <Row label="Min file size" hint="e.g. 400M / 1G">
          <Input value={form.cleanLessThan} onChange={(e) => patch("cleanLessThan", e.target.value)} style={{ maxWidth: 120 }} placeholder="400M" />
        </Row>
      </Section>

      <Section title="Telegram bot" label="Save & test" onSave={() => save("tg")} saved={saved.tg}>
        <Row label="Bot token" hint="Created via @BotFather">
          <Input type="password" value={form.botToken} onChange={(e) => patch("botToken", e.target.value)} placeholder="your_bot_token" />
        </Row>
        <Row label="Allowed user ID" hint="Get yours from @getidsbot — numeric">
          <Input value={form.allowedUser} onChange={(e) => patch("allowedUser", e.target.value)} style={{ maxWidth: 220 }} />
        </Row>
      </Section>

      <Section
        title="115 open platform"
        hint="Enter App ID and tap Scan to authorise. Tokens are written automatically once granted."
        label="Save & test"
        onSave={() => save("p115")}
        saved={saved.p115}
      >
        <Row label="App ID">
          <Input value={form.appId} onChange={(e) => patch("appId", e.target.value)} placeholder="your_115_app_id" />
        </Row>
        <Row label="QR auth" hint="First-time auth or refresh expired tokens">
          <div className="row gap-3" style={{ alignItems: "center" }}>
            <Button variant="secondary" size="sm" icon={<RefreshCw className="icon" />}>Get QR code</Button>
            <Badge tone="success"><Lock className="icon" style={{ width: 10, height: 10 }} /> Authorised · 7d remaining</Badge>
          </div>
        </Row>
        <Row label="Access token">
          <Input type="password" value={form.accessToken} onChange={(e) => patch("accessToken", e.target.value)} placeholder="your_access_token" />
        </Row>
        <Row label="Refresh token">
          <Input type="password" value={form.refreshToken} onChange={(e) => patch("refreshToken", e.target.value)} placeholder="your_refresh_token" />
        </Row>
      </Section>

      <Section title="AI model" hint="Used for media-name recognition and other AI features." onSave={() => save("ai")} saved={saved.ai}>
        <Row label="API URL">
          <Input value={form.aiApiUrl} onChange={(e) => patch("aiApiUrl", e.target.value)} placeholder="https://api.siliconflow.cn/v1" />
        </Row>
        <Row label="API key">
          <Input type="password" value={form.aiApiKey} onChange={(e) => patch("aiApiKey", e.target.value)} placeholder="sk-xxxxxxxxxxxxxxxxxxx" />
        </Row>
        <Row label="Model">
          <Input value={form.aiModel} onChange={(e) => patch("aiModel", e.target.value)} placeholder="deepseek-ai/DeepSeek-V3.2" />
        </Row>
      </Section>
    </>
  );
}

window.Config = Config;
