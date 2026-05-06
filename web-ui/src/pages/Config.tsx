import { type ReactNode, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, RefreshCw, Save } from "lucide-react";

import { API_BASE_URL } from "../api/client";
import { systemApi } from "../api/queries";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  Input,
  LoadingState,
  PageHeader,
  Select,
  Switch,
} from "../components/ui";
import { cn, errorMessage } from "../lib/utils";

type FormState = {
  logLevel: string;
  webEnabled: boolean;
  webPort: string;
  webAuthKey: string;
  cleanEnabled: boolean;
  cleanLessThan: string;
  botToken: string;
  allowedUser: string;
  appId: string;
  accessToken: string;
  refreshToken: string;
  aiApiUrl: string;
  aiApiKey: string;
  aiModel: string;
};

function toFormState(config: Record<string, unknown>): FormState {
  const clean = (config.clean_policy ?? {}) as Record<string, unknown>;
  const web = (config.web ?? {}) as Record<string, unknown>;
  const ai = (config.ai ?? {}) as Record<string, unknown>;
  return {
    logLevel: (config.log_level as string) || "info",
    webEnabled: web.enable !== false,
    webPort: String(web.port ?? 8000),
    webAuthKey: (web.auth_key as string) || "",
    botToken: (config.bot_token as string) || "",
    allowedUser: String(config.allowed_user ?? ""),
    appId: (config["115_app_id"] as string) || "",
    accessToken: (config.access_token as string) || "",
    refreshToken: (config.refresh_token as string) || "",
    aiApiUrl: (ai.api_url as string) || "",
    aiApiKey: (ai.api_key as string) || "",
    aiModel: (ai.model as string) || "",
    cleanEnabled: (clean.switch as string) !== "off",
    cleanLessThan: (clean.less_than as string) || "400M",
  };
}

function toApiConfig(form: FormState, original: Record<string, unknown>): Record<string, unknown> {
  return {
    ...original,
    log_level: form.logLevel,
    web: { ...((original.web as object) || {}), enable: form.webEnabled, port: Number(form.webPort), auth_key: form.webAuthKey },
    bot_token: form.botToken,
    allowed_user: form.allowedUser,
    "115_app_id": form.appId,
    access_token: form.accessToken,
    refresh_token: form.refreshToken,
    ai: { ...((original.ai as object) || {}), api_url: form.aiApiUrl, api_key: form.aiApiKey, model: form.aiModel },
    clean_policy: { ...((original.clean_policy as object) || {}), switch: form.cleanEnabled ? "on" : "off", less_than: form.cleanLessThan },
  };
}

type TestResult = { ok: boolean; message: string };

function useSectionSave(label: string, testAfterSave?: () => Promise<TestResult>) {
  const queryClient = useQueryClient();
  const [justSaved, setJustSaved] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const mutation = useMutation({
    mutationFn: async (config: Record<string, unknown>) => {
      await systemApi.updateConfig(config);
      if (!testAfterSave) return null;
      try { return await testAfterSave(); }
      catch (error) { throw new Error(`已保存，但测试失败：${errorMessage(error)}`); }
    },
    onMutate: () => setTestResult(null),
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

  function patch<K extends keyof FormState>(key: K, value: FormState[K]) {
    setFormState((prev) => (prev ? { ...prev, [key]: value } : prev));
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
      <PageHeader
        title="系统配置"
        description="管理运行时配置。保存后立即生效，端口变更需要重启服务。"
      />

      {/* ── Basic ── */}
      <Section
        title="基础设置"
        hint="日志级别、Web 端口、访问密钥和广告文件清理策略。"
        saveState={mainSave}
        onSave={() => saveSection(mainSave)}
      >
        <Row label="日志级别">
          <Select
            value={formState.logLevel}
            onChange={(e) => patch("logLevel", e.target.value)}
            className="max-w-40"
          >
            {["debug", "info", "warning", "error", "critical"].map((l) => (
              <option key={l}>{l}</option>
            ))}
          </Select>
        </Row>
        <Row label="Web 端口" hint="重启服务后生效">
          <Input
            type="number"
            value={formState.webPort}
            onChange={(e) => patch("webPort", e.target.value)}
            className="max-w-28"
          />
        </Row>
        <Row label="启用 Web UI">
          <Switch checked={formState.webEnabled} onCheckedChange={(v) => patch("webEnabled", v)} />
        </Row>
        <Row label="Web 访问密钥" hint="留空则不启用认证。WEB_AUTH_KEY 环境变量优先。">
          <Input
            type="password"
            value={formState.webAuthKey}
            onChange={(e) => patch("webAuthKey", e.target.value)}
            placeholder="留空则关闭认证"
          />
        </Row>
        <Row label="广告清理" hint="自动删除小于阈值的文件">
          <Switch checked={formState.cleanEnabled} onCheckedChange={(v) => patch("cleanEnabled", v)} />
        </Row>
        <Row label="最小文件大小" hint="例如 400M / 1G">
          <Input
            value={formState.cleanLessThan}
            onChange={(e) => patch("cleanLessThan", e.target.value)}
            className="max-w-28"
            placeholder="400M"
          />
        </Row>
      </Section>

      {/* ── Telegram Bot ── */}
      <Section
        title="Telegram 机器人"
        saveState={tgSave}
        onSave={() => saveSection(tgSave)}
      >
        <Row label="Bot Token" hint="通过 @BotFather 创建">
          <Input
            type="password"
            value={formState.botToken}
            onChange={(e) => patch("botToken", e.target.value)}
            placeholder="填写 Bot Token"
          />
        </Row>
        <Row label="允许的用户 ID" hint="可通过 @getidsbot 获取，需填写数字 ID">
          <Input
            value={formState.allowedUser}
            onChange={(e) => patch("allowedUser", e.target.value)}
            className="max-w-56"
            placeholder="填写用户数字 ID"
          />
        </Row>
      </Section>

      {/* ── 115 Open Platform ── */}
      <Section
        title="115 开放平台"
        hint="填写 App ID 后扫码授权，授权成功后会自动写入 Token。"
        saveState={api115Save}
        onSave={() => saveSection(api115Save)}
      >
        <Row label="App ID">
          <Input
            value={formState.appId}
            onChange={(e) => patch("appId", e.target.value)}
            placeholder="填写 115 App ID"
          />
        </Row>
        <Row label="扫码授权" hint="首次授权或刷新过期 Token 时使用">
          <QrcodeAuth />
        </Row>
        <Row label="Access Token">
          <Input
            type="password"
            value={formState.accessToken}
            onChange={(e) => patch("accessToken", e.target.value)}
            placeholder="填写 Access Token"
          />
        </Row>
        <Row label="Refresh Token">
          <Input
            type="password"
            value={formState.refreshToken}
            onChange={(e) => patch("refreshToken", e.target.value)}
            placeholder="填写 Refresh Token"
          />
        </Row>
      </Section>

      {/* ── AI Model ── */}
      <Section
        title="AI 模型"
        hint="用于媒体名称识别和其他 AI 能力。"
        saveState={aiSave}
        onSave={() => saveSection(aiSave)}
      >
        <Row label="API 地址">
          <Input
            value={formState.aiApiUrl}
            onChange={(e) => patch("aiApiUrl", e.target.value)}
            placeholder="https://api.siliconflow.cn/v1"
          />
        </Row>
        <Row label="API Key">
          <Input
            type="password"
            value={formState.aiApiKey}
            onChange={(e) => patch("aiApiKey", e.target.value)}
            placeholder="sk-xxxxxxxxxxxxxxxxxxx"
          />
        </Row>
        <Row label="模型">
          <Input
            value={formState.aiModel}
            onChange={(e) => patch("aiModel", e.target.value)}
            placeholder="deepseek-ai/DeepSeek-V3.2"
          />
        </Row>
      </Section>
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
    <Card className="mb-4">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold">{title}</h2>
          {hint ? <p className="mt-1 max-w-lg break-words text-xs text-muted-foreground">{hint}</p> : null}
        </div>
        {onSave && saveState ? (
          <div className="flex max-w-full shrink-0 flex-col items-end gap-1">
            <Button size="sm" onClick={onSave} loading={saveState.mutation.isPending}>
              <Save className="h-3.5 w-3.5" />
              <span>{saveState.justSaved ? "已保存" : saveState.label}</span>
            </Button>
            {saveState.testResult ? (
              <p className="max-w-44 break-words text-right text-xs text-emerald-600">{saveState.testResult.message}</p>
            ) : null}
            {saveState.mutation.isError ? (
              <p className="max-w-44 break-words text-right text-xs text-rose-500">{errorMessage(saveState.mutation.error)}</p>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="config-rows">{children}</div>
    </Card>
  );
}

function Row({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="config-row">
      <div className="config-row-label">
        <p className="text-sm font-medium">{label}</p>
        {hint ? <p className="mt-1 break-words text-xs leading-snug text-muted-foreground">{hint}</p> : null}
      </div>
      <div className="config-row-control">{children}</div>
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
  idle: "", loading: "加载中", ready: "请用 115 App 扫码",
  waiting: "等待扫码", scanned: "已扫码，请在 App 内确认",
  success: "授权成功", expired: "二维码已过期", error: "出错",
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
    } catch (e) {
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
      setStatus("error"); setMessage("连接已中断");
      sse.close(); sseRef.current = null;
    };
  }

  useEffect(() => () => stopSSE(), []);

  const isPolling = status === "ready" || status === "waiting" || status === "scanned";
  const isDone = status === "success" || status === "expired" || status === "error";

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <Button
          size="sm"
          variant="secondary"
          onClick={startAuth}
          loading={status === "loading"}
          disabled={isPolling}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>{isDone || status === "idle" ? "获取二维码" : "授权中"}</span>
        </Button>
        {status !== "idle" ? (
          <Badge tone={QR_TONE[status] ?? "default"}>
            <KeyRound className="h-3 w-3" />
            {QR_LABEL[status] ?? status}
          </Badge>
        ) : null}
      </div>
      {qrB64 ? (
        <img
          src={`data:image/png;base64,${qrB64}`}
          alt="115 授权二维码"
          className="h-40 w-40 rounded-lg border border-white/30 shadow"
        />
      ) : null}
      {message && status !== "idle" ? (
        <p
          className={cn(
            "text-xs",
            status === "success" ? "text-emerald-600" :
            status === "error" || status === "expired" ? "text-rose-500" :
            "text-muted-foreground",
          )}
        >
          {message}
        </p>
      ) : null}
    </div>
  );
}
