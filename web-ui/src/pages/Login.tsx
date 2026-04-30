import { FormEvent, useState } from "react";
import { KeyRound, LogIn } from "lucide-react";

import { authApi } from "../api/queries";
import { Button, Card, ErrorState, Input } from "../components/ui";

export function Login({ onLogin }: { onLogin: (key: string) => void }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedKey = key.trim();
    if (!trimmedKey) {
      setError("请输入认证密钥");
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
    <main className="flex min-h-screen items-center justify-center px-4 text-foreground">
      <div className="w-full max-w-sm">
        <div className="mb-5 flex items-center gap-3">
          <img
            className="h-14 w-14 rounded-xl shadow-glass"
            src="/brand/sehuatang-115-bot.svg"
            alt="Reaper115"
          />
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Reaper115</h1>
            <p className="text-sm text-muted-foreground">请输入 Web UI 认证密钥</p>
          </div>
        </div>

        <Card className="shadow-glass">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <label className="flex items-center gap-2 text-sm font-medium" htmlFor="web-auth-key">
                <KeyRound className="h-4 w-4 text-primary" />
                <span>认证密钥</span>
              </label>
              <Input
                id="web-auth-key"
                type="password"
                autoComplete="current-password"
                autoFocus
                value={key}
                onChange={(event) => setKey(event.target.value)}
              />
            </div>

            {error ? <ErrorState message={error} /> : null}

            <Button className="w-full" loading={loading} type="submit">
              {loading ? null : <LogIn className="h-4 w-4" />}
              登录
            </Button>
          </form>
        </Card>
      </div>
    </main>
  );
}
