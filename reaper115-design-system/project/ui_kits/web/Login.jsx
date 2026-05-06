// Login screen: minimal centered card, password field, primary submit.
// Echoes pages/Login.tsx — single password (no username), error inline.
const { Lock, Shield, Eye, EyeOff } = window.R115Icons;

function Login() {
  const [show, setShow] = React.useState(false);
  const [val, setVal]   = React.useState("");
  return (
    <div className="login-stage">
      <Card large className="login-card">
        <div className="login-mark">
          <img src="../../assets/logo/sehuatang-115-bot-256.png" alt="Reaper115" />
          <div>
            <h1>Sign in</h1>
            <p>Reaper115 admin console</p>
          </div>
        </div>

        <Field label="Password" icon={<Lock className="icon" />}>
          <div style={{ position: "relative" }}>
            <input
              className="input"
              type={show ? "text" : "password"}
              value={val}
              onChange={(e) => setVal(e.target.value)}
              placeholder="••••••••"
              style={{ paddingRight: 36 }}
            />
            <button
              type="button"
              onClick={() => setShow(!show)}
              className="icon-btn"
              style={{ position: "absolute", right: 4, top: 2 }}
              aria-label={show ? "Hide password" : "Show password"}
            >
              {show ? <EyeOff className="icon" /> : <Eye className="icon" />}
            </button>
          </div>
        </Field>

        <Button className="primary" style={{ width: "100%", marginTop: 16 }} icon={<Shield className="icon" />}>
          Sign in
        </Button>

        <div style={{ marginTop: 12, fontSize: 12, color: "hsl(var(--muted-foreground))", textAlign: "center" }}>
          Sessions persist for 7 days · TLS only
        </div>
      </Card>
    </div>
  );
}

window.Login = Login;
