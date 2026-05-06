// Reusable atoms that mirror the project's web-ui/src/components/ui.tsx
// (Button, Card, Badge, Input, Select, Switch, EmptyState…) but as plain JSX.
// Style application lives in web-kit.css; we just compose class names here.
const cx = (...xs) => xs.filter(Boolean).join(" ");

function Button({ variant = "primary", size = "md", icon, children, className, ...rest }) {
  return (
    <button
      className={cx("btn", variant, size === "sm" && "sm", !children && "icon", className)}
      {...rest}
    >
      {icon}{children && <span>{children}</span>}
    </button>
  );
}

function Card({ children, className, large = false, ...rest }) {
  return <div className={cx("card", large && "card-lg", className)} {...rest}>{children}</div>;
}

function CardSoft({ children, className, ...rest }) {
  return <div className={cx("card-soft", className)} {...rest}>{children}</div>;
}

function Badge({ tone = "default", children }) {
  return <span className={cx("badge", tone)}>{children}</span>;
}

function Input({ ...rest }) {
  return <input className="input" {...rest} />;
}

function Select({ children, ...rest }) {
  return <select className="select" {...rest}>{children}</select>;
}

function Textarea({ ...rest }) {
  return <textarea className="textarea" {...rest} />;
}

function Switch({ on, onChange }) {
  return (
    <button
      className={cx("switch", on ? "on" : "off")}
      onClick={() => onChange?.(!on)}
      aria-pressed={on}
      aria-label="Toggle"
      type="button"
    >
      <span className="switch-knob"></span>
    </button>
  );
}

function EmptyState({ icon, title, hint }) {
  return (
    <div className="empty">
      {icon && <div style={{ marginBottom: 8 }}>{icon}</div>}
      <div style={{ color: "var(--r115-ink)", fontWeight: 500 }}>{title}</div>
      {hint && <div style={{ marginTop: 4 }}>{hint}</div>}
    </div>
  );
}

function Field({ label, icon, children }) {
  return (
    <label style={{ display: "block" }}>
      <div className="field-label">{icon}<span>{label}</span></div>
      {children}
    </label>
  );
}

function StatCard({ label, value, icon, tone = "primary" }) {
  return (
    <Card className="stat-card">
      <div>
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
      </div>
      <div className={cx("stat-icon", tone)}>{icon}</div>
    </Card>
  );
}

function PageHeader({ title, desc, actions }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {desc && <div className="desc">{desc}</div>}
      </div>
      {actions && <div className="actions">{actions}</div>}
    </header>
  );
}

Object.assign(window, { Button, Card, CardSoft, Badge, Input, Select, Textarea, Switch, EmptyState, Field, StatCard, PageHeader, cx });
