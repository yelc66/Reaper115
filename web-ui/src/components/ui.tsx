import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { Children, useEffect, useRef } from "react";
import { Loader2, X } from "lucide-react";

import { cn } from "../lib/utils";

export function Button({
  className,
  variant = "primary",
  size = "md",
  loading,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "icon";
  loading?: boolean;
}) {
  return (
    <button
      className={cn(
        "inline-flex min-w-0 shrink-0 items-center justify-center gap-2 overflow-hidden rounded-md text-sm font-medium transition duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-40 [&>span]:min-w-0 [&>span]:truncate",
        variant === "primary" &&
          "bg-primary text-white shadow-[var(--shadow-cta)] hover:-translate-y-0.5 hover:bg-[#0070F0] hover:shadow-[var(--shadow-cta-hover)] active:translate-y-0 active:bg-[#0066D9]",
        variant === "secondary" &&
          "border border-[var(--glass-border)] bg-white/58 text-foreground shadow-[var(--shadow-card-soft)] backdrop-blur-xl hover:-translate-y-0.5 hover:bg-white/72",
        variant === "ghost" &&
          "border border-transparent bg-transparent text-muted-foreground hover:bg-white/55 hover:text-foreground",
        variant === "danger" &&
          "border border-rose-500/20 bg-rose-500/10 text-rose-600 hover:bg-rose-500/18",
        size === "sm" && "h-7 px-2.5 text-xs",
        size === "md" && "h-8 max-w-full px-3.5",
        size === "icon" && "h-8 w-8 p-0",
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
      {Children.map(children, (child) =>
        typeof child === "string" || typeof child === "number" ? <span>{child}</span> : child,
      )}
    </button>
  );
}

export function Card({
  className,
  large,
  children,
  ...rest
}: {
  className?: string;
  large?: boolean;
  children: ReactNode;
  [key: string]: unknown;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--glass-border)] bg-[var(--glass-fill-card)] shadow-panel backdrop-blur-[var(--glass-blur)]",
        large ? "p-5" : "p-4",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardSoft({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--glass-border)] bg-white/58 p-4",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        <h1 className="break-words text-xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? (
          <p className="mt-0.5 break-words text-[13px] text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex max-w-full flex-wrap items-center justify-end gap-2">{actions}</div>
      ) : null}
    </div>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-8 w-full min-w-0 rounded-md border border-[var(--glass-border)] bg-white/62 px-3 text-sm text-foreground outline-none backdrop-blur-xl transition placeholder:text-muted-foreground focus:border-primary/60 focus:ring-2 focus:ring-primary/15",
        className,
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-8 w-full min-w-0 rounded-md border border-[var(--glass-border)] bg-white/62 px-3 text-sm text-foreground outline-none backdrop-blur-xl transition focus:border-primary/60 focus:ring-2 focus:ring-primary/15",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-[90px] w-full min-w-0 rounded-md border border-[var(--glass-border)] bg-white/62 px-3 py-2 font-mono text-[13px] text-foreground outline-none backdrop-blur-xl transition placeholder:text-muted-foreground focus:border-primary/60 focus:ring-2 focus:ring-primary/15",
        className,
      )}
      {...props}
    />
  );
}

export function Switch({
  checked,
  onCheckedChange,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
        checked ? "bg-primary" : "bg-muted-foreground/30",
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200",
          checked ? "translate-x-[18px]" : "translate-x-[2px]",
        )}
      />
    </button>
  );
}

export function Badge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "info";
}) {
  return (
    <span
      className={cn(
        "inline-flex h-5 max-w-full items-center gap-1 rounded px-1.5 text-xs font-medium tracking-wide",
        tone === "default" && "border border-white/55 bg-white/55 text-muted-foreground backdrop-blur-xl",
        tone === "success" && "bg-emerald-500/12 text-emerald-700",
        tone === "warning" && "bg-amber-500/12 text-amber-700",
        tone === "danger" && "bg-rose-500/12 text-rose-600",
        tone === "info" && "bg-primary/10 text-primary",
      )}
    >
      {children}
    </span>
  );
}

export function StatCard({
  label,
  value,
  icon,
  tone = "primary",
}: {
  label: string;
  value: string | number;
  icon: ReactNode;
  tone?: "primary" | "success" | "warning" | "danger" | "default";
}) {
  return (
    <Card className="flex items-center justify-between">
      <div className="min-w-0">
        <div className="truncate text-[13px] text-muted-foreground">{label}</div>
        <div className="mt-2 truncate text-3xl font-semibold tracking-tight">{value}</div>
      </div>
      <div
        className={cn(
          "h-8 w-8 shrink-0",
          tone === "primary" && "text-primary",
          tone === "success" && "text-emerald-500",
          tone === "warning" && "text-amber-500",
          tone === "danger" && "text-rose-500",
          tone === "default" && "text-muted-foreground",
        )}
      >
        {icon}
      </div>
    </Card>
  );
}

export function Field({
  label,
  icon,
  children,
}: {
  label: string;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-center gap-2 text-sm font-medium text-foreground">
        {icon ? <span className="text-primary [&>svg]:h-3.5 [&>svg]:w-3.5">{icon}</span> : null}
        <span className="min-w-0 break-words">{label}</span>
      </div>
      {children}
    </label>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
      {children}
    </div>
  );
}

export function LoadingState() {
  return (
    <div className="flex h-40 items-center justify-center text-muted-foreground">
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      <span className="text-sm">加载中</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-rose-500/20 bg-rose-500/8 p-3 text-sm text-rose-600">
      {message}
    </div>
  );
}

export function Drawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-[2px]"
        onClick={onClose}
      />
      {/* Panel */}
      <div
        ref={drawerRef}
        className="relative z-10 flex h-full w-full max-w-md flex-col overflow-hidden border-l border-[var(--glass-border)] bg-white/90 shadow-2xl backdrop-blur-xl"
      >
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
          <h2 className="text-base font-semibold text-foreground">{title}</h2>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition hover:bg-black/6 hover:text-foreground"
            aria-label="关闭"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

export function DrawerField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-4">
      <div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="text-sm text-foreground">{children}</div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  danger,
}: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
      if (e.key === "Enter") onConfirm();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onCancel, onConfirm]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-[2px]"
        onClick={onCancel}
      />
      <div className="relative z-10 w-full max-w-sm rounded-xl border border-[var(--glass-border)] bg-white/92 p-6 shadow-2xl backdrop-blur-xl">
        <h3 className="mb-2 text-base font-semibold text-foreground">{title}</h3>
        <div className="mb-5 text-sm text-muted-foreground">{message}</div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel}>
            取消
          </Button>
          <Button
            variant={danger ? "danger" : "primary"}
            size="sm"
            onClick={onConfirm}
          >
            {confirmLabel ?? "确认"}
          </Button>
        </div>
      </div>
    </div>
  );
}
