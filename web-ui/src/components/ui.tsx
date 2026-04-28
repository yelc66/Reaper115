import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";

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
        "inline-flex shrink-0 items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-40",
        variant === "primary" &&
          "bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/80",
        variant === "secondary" &&
          "border border-border bg-surface-elevated text-foreground hover:bg-surface-elevated/80",
        variant === "ghost" &&
          "border border-transparent bg-transparent text-muted-foreground hover:bg-surface-elevated hover:text-foreground",
        variant === "danger" &&
          "bg-destructive/10 text-red-400 border border-destructive/20 hover:bg-destructive/20",
        size === "sm" && "h-7 px-2.5 text-xs",
        size === "md" && "h-8 px-3.5",
        size === "icon" && "h-8 w-8 p-0",
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
      {children}
    </button>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("rounded-lg border border-border bg-surface p-4 shadow-panel", className)}>
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
    <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? <p className="mt-0.5 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-8 w-full rounded-md border border-border bg-surface-elevated px-3 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:border-primary/60 focus:ring-2 focus:ring-primary/15",
        className,
      )}
      {...props}
    />
  );
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-8 w-full rounded-md border border-border bg-surface-elevated px-3 text-sm text-foreground outline-none transition focus:border-primary/60 focus:ring-2 focus:ring-primary/15",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-28 w-full rounded-md border border-border bg-surface-elevated px-3 py-2 font-mono text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:border-primary/60 focus:ring-2 focus:ring-primary/15",
        className,
      )}
      {...props}
    />
  );
}

export function Badge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded px-1.5 text-xs font-medium tracking-wide",
        tone === "default" && "bg-surface-elevated text-muted-foreground",
        tone === "success" && "bg-emerald-500/12 text-emerald-400",
        tone === "warning" && "bg-amber-500/12 text-amber-400",
        tone === "danger" && "bg-rose-500/12 text-rose-400",
      )}
    >
      {children}
    </span>
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
    <div className="rounded-md border border-rose-500/20 bg-rose-500/8 p-3 text-sm text-rose-400">
      {message}
    </div>
  );
}
