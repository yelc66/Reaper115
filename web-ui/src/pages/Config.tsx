import { type ReactNode, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, RefreshCw, Save } from "lucide-react";

import { API_BASE_URL } from "../api/client";
import { systemApi } from "../api/queries";
import { Badge, Button, Card, ErrorState, Input, LoadingState, PageHeader, Select } from "../components/ui";
import { cn, errorMessage } from "../lib/utils";

type FormState = {
  logLevel: string;
  webEnabled: boolean;
  webPort: string;
  webAuthKey: string;
  botToken: string;
  allowedUser: string;
  appId: string;
  accessToken: string;
  refreshToken: string;
  aiApiUrl: string;
  aiApiKey: string;
  aiModel: string;
  cleanEnabled: boolean;
  cleanLessThan: string;
};

function toFormState(config: Record<string, unknown>): FormState {
  const cleanPolicy = (config.clean_policy ?? {}) as Record<string, unknown>;
  const webConfig = (config.web ?? {}) as Record<string, unknown>;
  const aiConfig = (config.ai ?? {}) as Record<string, unknown>;

  return {
    logLevel: (config.log_level as string) || "info",
    webEnabled: webConfig.enable !== false,
    webPort: String(webConfig.port ?? 8000),
    webAuthKey: (webConfig.auth_key as string) || "",
    botToken: (config.bot_token as string) || "",
    allowedUser: String(config.allowed_user ?? ""),
    appId: (config["115_app_id"] as string) || "",
    accessToken: (config.access_token as string) || "",
    refreshToken: (config.refresh_token as string) || "",
    aiApiUrl: (aiConfig.api_url as string) || "",
    aiApiKey: (aiConfig.api_key as string) || "",
    aiModel: (aiConfig.model as string) || "",
    cleanEnabled: (cleanPolicy.switch as string) !== "off",
    cleanLessThan: (cleanPolicy.less_than as string) || "400M",
  };
}

function toApiConfig(formState: FormState, original: Record<string, unknown>): Record<string, unknown> {
  return {
    ...original,
    log_level: formState.logLevel,
    web: {
      ...((original.web as object) || {}),
      enable: formState.webEnabled,
      port: Number(formState.webPort),
      auth_key: formState.webAuthKey,
    },
    bot_token: formState.botToken,
    allowed_user: formState.allowedUser,
    "115_app_id": formState.appId,
    access_token: formState.accessToken,
    refresh_token: formState.refreshToken,
    ai: {
      ...((original.ai as object) || {}),
      api_url: formState.aiApiUrl,
      api_key: formState.aiApiKey,
      model: formState.aiModel,
    },
    clean_policy: {
      switch: formState.cleanEnabled ? "on" : "off",
      less_than: formState.cleanLessThan,
    },
  };
}

type TestResult = {
  ok: boolean;
  message: string;
};

function useSectionSave(label: string, testAfterSave?: () => Promise<TestResult>) {
  const queryClient = useQueryClient();
  const [justSaved, setJustSaved] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const mutation = useMutation({
    mutationFn: async (config: Record<string, unknown>) => {
      await systemApi.updateConfig(config);
      if (!testAfterSave) return null;
      try {
        return await testAfterSave();
      } catch (error) {
        throw new Error(`配置已保存，但测试失败：${errorMessage(error)}`);
      }
    },
    onMutate: () => {
      setTestResult(null);
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["system"] });
      setTestResult(result);
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
    },
  });
  return { mutation, justSaved, label, testResult };
}

export function Config() {
  const [formState, setFormState] = useState<FormState | null>(null);
  const [original, setOriginal] = useState<Record<string, unknown>>({});

  const configQuery = useQuery({ queryKey: ["system", "config"], queryFn: systemApi.config });
  const mainSave = useSectionSave("保存");
  const tgSave = useSectionSave("保存并测试", systemApi.testTelegram);
  const api115Save = useSectionSave("保存并测试", systemApi.test115);
  const aiSave = useSectionSave("保存");

  useEffect(() => {
    if (configQuery.data?.config) {
      setOriginal(configQuery.data.config);
      setFormState(toFormState(configQuery.data.config));
    }
  }, [configQuery.data]);

  function patchForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setFormState((previous) => (previous ? { ...previous, [key]: value } : previous));
  }

  function saveSection(save: ReturnType<typeof useSectionSave>) {
    if (!formState) return;
    save.mutation.mutate(toApiConfig(formState, original));
  }

  if (configQuery.isPending) return <LoadingState />;
  if (configQuery.isError) return <ErrorState message={errorMessage(configQuery.error)} />;
  if (!formState) return null;

  return (
    <>
      <PageHeader title="配置管理" description="管理机器人运行配置，保存后立即生效（端口等需重启）" />
      <div className="space-y-4">
        {/* 基础 + 广告清理 */}
        <Section title="基础设置" onSave={() => saveSection(mainSave)} saveState={mainSave}>
          <Row label="日志级别">
            <Select
              value={formState.logLevel}
              onChange={(event) => patchForm("logLevel", event.target.value)}
              className="max-w-40"
            >
              {["debug", "info", "warning", "error", "critical"].map((level) => (
                <option key={level}>{level}</option>
              ))}
            </Select>
          </Row>
          <Row label="Web 界面端口" hint="重启后生效">
            <Input
              type="number"
              value={formState.webPort}
              onChange={(event) => patchForm("webPort", event.target.value)}
              className="max-w-32"
            />
          </Row>
          <Row label="开启 Web 界面">
            <Switch
              checked={formState.webEnabled}
              onCheckedChange={(checked) => patchForm("webEnabled", checked)}
            />
          </Row>
          <Row label="Web 认证密钥" hint="留空表示不启用登录认证；WEB_AUTH_KEY 环境变量优先">
            <Input
              type="password"
              value={formState.webAuthKey}
              onChange={(event) => patchForm("webAuthKey", event.target.value)}
              placeholder="留空不启用"
            />
          </Row>
          <Row label="开启广告清理">
            <Switch
              checked={formState.cleanEnabled}
              onCheckedChange={(checked) => patchForm("cleanEnabled", checked)}
            />
          </Row>
          <Row label="最小文件大小" hint="小于此值视为广告自动删除，如 400M / 1G">
            <Input
              value={formState.cleanLessThan}
              onChange={(event) => patchForm("cleanLessThan", event.target.value)}
              className="max-w-32"
              placeholder="400M"
            />
          </Row>
        </Section>

        {/* Telegram Bot — 独立保存 */}
        <Section title="Telegram Bot" onSave={() => saveSection(tgSave)} saveState={tgSave}>
          <Row label="Bot Token" hint="@BotFather 创建">
            <Input
              type="password"
              value={formState.botToken}
              onChange={(event) => patchForm("botToken", event.target.value)}
              placeholder="your_bot_token"
            />
          </Row>
          <Row label="授权用户 ID" hint="@getidsbot 获取，数字类型">
            <Input
              value={formState.allowedUser}
              onChange={(event) => patchForm("allowedUser", event.target.value)}
              placeholder="your_user_id"
              className="max-w-56"
            />
          </Row>
        </Section>

        {/* 115 开放平台 — 独立保存 */}
        <Section title="115 开放平台" hint="填写 App ID 后点击「扫码授权」完成首次授权，Token 会自动写入" onSave={() => saveSection(api115Save)} saveState={api115Save}>
          <Row label="App ID">
            <Input
              value={formState.appId}
              onChange={(event) => patchForm("appId", event.target.value)}
              placeholder="your_115_app_id"
            />
          </Row>
          {formState.appId && formState.appId !== "your_115_app_id" ? (
            <Row label="扫码授权" hint="首次授权或 Token 过期时使用">
              <QrcodeAuth />
            </Row>
          ) : (
            <>
              <Row label="Access Token">
                <Input
                  type="password"
                  value={formState.accessToken}
                  onChange={(event) => patchForm("accessToken", event.target.value)}
                  placeholder="your_access_token"
                />
              </Row>
              <Row label="Refresh Token">
                <Input
                  type="password"
                  value={formState.refreshToken}
                  onChange={(event) => patchForm("refreshToken", event.target.value)}
                  placeholder="your_refresh_token"
                />
              </Row>
            </>
          )}
        </Section>


        <Section title="AI 模型配置" hint="用于媒体名称识别等 AI 能力" onSave={() => saveSection(aiSave)} saveState={aiSave}>
          <Row label="API 地址">
            <Input
              value={formState.aiApiUrl}
              onChange={(event) => patchForm("aiApiUrl", event.target.value)}
              placeholder="https://api.siliconflow.cn/v1"
            />
          </Row>
          <Row label="API Key">
            <Input
              type="password"
              value={formState.aiApiKey}
              onChange={(event) => patchForm("aiApiKey", event.target.value)}
              placeholder="sk-xxxxxxxxxxxxxxxxxxx"
            />
          </Row>
          <Row label="模型">
            <Input
              value={formState.aiModel}
              onChange={(event) => patchForm("aiModel", event.target.value)}
              placeholder="deepseek-ai/DeepSeek-V3.2"
            />
          </Row>
        </Section>

      </div>
    </>
  );
}

type SectionSaveState = ReturnType<typeof useSectionSave>;

function Section({
  title,
  hint,
  children,
  onSave,
  saveState,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
  onSave?: () => void;
  saveState?: SectionSaveState;
}) {
  return (
    <Card>
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
        </div>
        {onSave && saveState ? (
          <div className="flex shrink-0 flex-col items-end gap-1">
            <Button size="sm" onClick={onSave} loading={saveState.mutation.isPending}>
              <Save className="h-3.5 w-3.5" />
              {saveState.justSaved ? "已保存 ✓" : saveState.label}
            </Button>
            {saveState.testResult ? (
              <p className="text-xs text-emerald-500">{saveState.testResult.message}</p>
            ) : null}
            {saveState.mutation.isError ? (
              <p className="text-xs text-rose-500">{errorMessage(saveState.mutation.error)}</p>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="divide-y divide-border">{children}</div>
    </Card>
  );
}

function Row({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 py-5 sm:flex-row sm:items-start sm:gap-10">
      <div className="sm:w-40 sm:shrink-0">
        <p className="text-sm font-medium">{label}</p>
        {hint ? <p className="mt-1 text-xs leading-snug text-muted-foreground">{hint}</p> : null}
      </div>
      <div className="flex flex-1 items-center">{children}</div>
    </div>
  );
}

type QrStatus = "idle" | "loading" | "ready" | "waiting" | "scanned" | "success" | "expired" | "error";
type PollResult = { status: string; done: boolean; message: string };

const QR_TONE: Record<string, "success" | "warning" | "danger" | "default"> = {
  ready: "default", waiting: "default", scanned: "warning",
  success: "success", expired: "danger", error: "danger",
};
const QR_LABEL: Record<string, string> = {
  idle: "", loading: "获取中...", ready: "请用115 APP扫码",
  waiting: "等待扫码...", scanned: "已扫码，等待确认...",
  success: "授权成功！", expired: "二维码已过期", error: "出错了",
};

function QrcodeAuth() {
  const [qrB64, setQrB64] = useState<string | null>(null);
  const [status, setStatus] = useState<QrStatus>("idle");
  const [message, setMessage] = useState("");
  const sseRef = useRef<EventSource | null>(null);

  function stopSSE() {
    sseRef.current?.close();
    sseRef.current = null;
  }

  async function startAuth() {
    stopSSE();
    setStatus("loading");
    setQrB64(null);
    setMessage("");
    try {
      const res = await systemApi.get115Qrcode();
      setQrB64(res.qr_b64);
      setStatus("ready");
    } catch (e: unknown) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : String(e));
      return;
    }
    const sse = new EventSource(`${API_BASE_URL}/api/system/115/qrcode/status`);
    sseRef.current = sse;
    sse.onmessage = (event) => {
      const result = JSON.parse(event.data) as PollResult;
      setStatus(result.status as QrStatus);
      setMessage(result.message);
      if (result.done) { sse.close(); sseRef.current = null; }
    };
    sse.onerror = () => {
      setStatus("error"); setMessage("连接中断");
      sse.close(); sseRef.current = null;
    };
  }

  useEffect(() => () => stopSSE(), []);

  const isPolling = status === "ready" || status === "waiting" || status === "scanned";
  const isDone = status === "success" || status === "expired" || status === "error";

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <Button size="sm" variant="secondary" onClick={startAuth} loading={status === "loading"} disabled={isPolling}>
          <RefreshCw className="h-3.5 w-3.5" />
          {isDone || status === "idle" ? "获取二维码" : "授权中..."}
        </Button>
        {status !== "idle" && (
          <Badge tone={QR_TONE[status] ?? "default"}>
            <KeyRound className="mr-1 h-3 w-3" />
            {QR_LABEL[status] ?? status}
          </Badge>
        )}
      </div>
      {qrB64 && (
        <img src={`data:image/png;base64,${qrB64}`} alt="115授权二维码"
          className="h-40 w-40 rounded-lg border border-white/30 shadow" />
      )}
      {message && status !== "idle" && (
        <p className={cn("text-xs", status === "success" ? "text-emerald-400" : status === "error" || status === "expired" ? "text-rose-400" : "text-muted-foreground")}>
          {message}
        </p>
      )}
    </div>
  );
}

function Switch({
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
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
        checked ? "bg-primary" : "bg-muted-foreground/30",
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
          checked ? "translate-x-4" : "translate-x-0",
        )}
      />
    </button>
  );
}
