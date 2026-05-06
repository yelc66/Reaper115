import { FormEvent, useState } from "react";
import { Eye, EyeOff, Lock, Shield } from "lucide-react";

import { authApi } from "../api/queries";
import { Button, Card, ErrorState, Field, Input } from "../components/ui";

export function Login({ onLogin }: { onLogin: (key: string) => void }) {
  const [key, setKey] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedKey = key.trim();
    if (!trimmedKey) {
      setError("请输入访问密码");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await authApi.login(trimmedKey);
      onLogin(trimmedKey);
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 text-foreground">
      <div className="w-full max-w-sm">
        <Card large>
          {/* Logo mark */}
          <div className="mb-5 flex items-center gap-3">
            <img
              className="h-14 w-14 rounded-xl shadow-glass"
              src="/brand/sehuatang-115-bot.svg"
              alt="Reaper115"
            />
            <div>
              <h1 className="text-xl font-semibold tracking-tight">登录</h1>
              <p className="text-[13px] text-muted-foreground">Reaper115 管理控制台</p>
            </div>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <Field label="访问密码" icon={<Lock />}>
              <div className="relative">
                <Input
                  type={show ? "text" : "password"}
                  autoComplete="current-password"
                  autoFocus
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                  placeholder="••••••••"
                  className="pr-9"
                />
                <button
                  type="button"
                  onClick={() => setShow(!show)}
                  className="absolute right-2 top-1 inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-foreground"
                  aria-label={show ? "隐藏密码" : "显示密码"}
                >
                  {show ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              </div>
            </Field>

            {error ? <ErrorState message={error} /> : null}

            <Button className="w-full" loading={loading} type="submit">
              {loading ? null : <Shield className="h-4 w-4" />}
              登录
            </Button>
          </form>

          <p className="mt-3 text-center text-xs text-muted-foreground">
            会话保留 7 天 · 请使用安全连接访问
          </p>
        </Card>
      </div>
    </main>
  );
}
