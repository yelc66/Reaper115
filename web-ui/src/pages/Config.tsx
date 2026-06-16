import { type ReactNode, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, KeyRound, RefreshCw, Save } from "lucide-react";

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

const DEFAULT_REMOTE_SELENIUM_URL = "http://chrome:4444";

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
  remoteSeleniumUrl: string;
  flareSolverrUrl: string;
};

function toFormState(config: Record<string, unknown>): FormState {
  const clean = (config.clean_policy ?? {}) as Record<string, unknown>;
  const web = (config.web ?? {}) as Record<string, unknown>;
  return {
    logLevel: (config.log_level as string) || "info",
    webEnabled: web.enable !== false,
    webPort: String(web.port ?? 8115),
    webAuthKey: (web.auth_key as string) || "",
    botToken: (config.bot_token as string) || "",
    allowedUser: String(config.allowed_user ?? ""),
    appId: (config["115_app_id"] as string) || "",
    accessToken: (config.access_token as string) || "",
    refreshToken: (config.refresh_token as string) || "",
    cleanEnabled: (clean.switch as string) !== "off",
    cleanLessThan: (clean.less_than as string) || "400M",
    remoteSeleniumUrl: (config.remote_selenium_url as string) || DEFAULT_REMOTE_SELENIUM_URL,
    flareSolverrUrl: (config.flaresolverr_url as string) || "",
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
    clean_policy: { ...((original.clean_policy as object) || {}), switch: form.cleanEnabled ? "on" : "off", less_than: form.cleanLessThan },
    remote_selenium_url: form.remoteSeleniumUrl,
    flaresolverr_url: form.flareSolverrUrl,
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
  const [savedState, setSavedState] = useState<FormState | null>(null);
  const [original, setOriginal] = useState<Record<string, unknown>>({});

  const configQuery = useQuery({ queryKey: ["system", "config"], queryFn: systemApi.config });
  const mainSave = useSectionSave("保存");
  const tgSave = useSectionSave("保存并测试", systemApi.testTelegram);
  const api115Save = useSectionSave("保存并测试", systemApi.test115);
  const browserSave = useSectionSave("保存");

  useEffect(() => {
    if (configQuery.data?.config) {
      const parsed = toFormState(configQuery.data.config);
      setOriginal(configQuery.data.config);
      setFormState(parsed);
      setSavedState(parsed);
    }
  }, [configQuery.data]);

  function patch<K extends keyof FormState>(key: K, value: FormState[K]) {
    setFormState((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function isDirty(keys: (keyof FormState)[]) {
    if (!formState || !savedState) return false;
    return keys.some((k) => formState[k] !== savedState[k]);
  }

  function saveSection(save: ReturnType<typeof useSectionSave>, keys: (keyof FormState)[]) {
    if (!formState) return;
    save.mutation.mutate(toApiConfig(formState, original));
    // optimistically mark as saved so dirty indicator resets
    setSavedState((prev) => {
      if (!prev || !formState) return prev;
      const next = { ...prev };
      for (const k of keys) (next as Record<string, unknown>)[k] = formState[k];
      return next;
    });
  }

  if (configQuery.isPending) return <LoadingState />;
  if (configQuery.isError) return <ErrorState message={errorMessage(configQuery.error)} />;
  if (!formState) return null;

  const mainKeys: (keyof FormState)[] = ["logLevel", "webEnabled", "webPort", "webAuthKey", "cleanEnabled", "cleanLessThan"];
  const tgKeys: (keyof FormState)[] = ["botToken", "allowedUser"];
  const api115Keys: (keyof FormState)[] = ["appId", "accessToken", "refreshToken"];
  const browserKeys: (keyof FormState)[] = ["remoteSeleniumUrl", "flareSolverrUrl"];

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
        dirty={isDirty(mainKeys)}
        onSave={() => saveSection(mainSave, mainKeys)}
      >
        <Row label="日志级别" fieldId="log-level">
          <Select
            id="log-level"
            value={formState.logLevel}
            onChange={(e) => patch("logLevel", e.target.value)}
            className="max-w-40"
          >
            {["debug", "info", "warning", "error", "critical"].map((l) => (
              <option key={l}>{l}</option>
            ))}
          </Select>
        </Row>
        <Row label="Web 端口" hint="重启服务后生效" fieldId="web-port">
          <Input
            id="web-port"
            type="number"
            value={formState.webPort}
            onChange={(e) => patch("webPort", e.target.value)}
            className="max-w-28"
          />
        </Row>
        <Row label="启用 Web UI" fieldId="web-enabled">
          <Switch checked={formState.webEnabled} onCheckedChange={(v) => patch("webEnabled", v)} />
        </Row>
        <Row label="Web 访问密钥" hint="留空则不启用认证。WEB_AUTH_KEY 环境变量优先。" fieldId="web-auth-key">
          <SecretInput
            id="web-auth-key"
            value={formState.webAuthKey}
            onChange={(v) => patch("webAuthKey", v)}
            placeholder="留空则关闭认证"
          />
        </Row>
        <Row label="广告清理" hint="自动删除小于阈值的文件" fieldId="clean-enabled">
          <Switch checked={formState.cleanEnabled} onCheckedChange={(v) => patch("cleanEnabled", v)} />
        </Row>
        <Row label="最小文件大小" hint="例如 400M / 1G" fieldId="clean-less-than">
          <Input
            id="clean-less-than"
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
        dirty={isDirty(tgKeys)}
        onSave={() => saveSection(tgSave, tgKeys)}
      >
        <Row label="Bot Token" hint="通过 @BotFather 创建" fieldId="bot-token">
          <SecretInput
            id="bot-token"
            value={formState.botToken}
            onChange={(v) => patch("botToken", v)}
            placeholder="填写 Bot Token"
          />
        </Row>
        <Row label="允许的用户 ID" hint="可通过 @getidsbot 获取，需填写数字 ID" fieldId="allowed-user">
          <Input
            id="allowed-user"
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
        dirty={isDirty(api115Keys)}
        onSave={() => saveSection(api115Save, api115Keys)}
      >
        <Row label="App ID" fieldId="app-id">
          <Input
            id="app-id"
            value={formState.appId}
            onChange={(e) => patch("appId", e.target.value)}
            placeholder="填写 115 App ID"
          />
        </Row>
        <Row label="扫码授权" hint="首次授权或刷新过期 Token 时使用">
          <QrcodeAuth />
        </Row>
        <Row label="Access Token" fieldId="access-token">
          <SecretInput
            id="access-token"
            value={formState.accessToken}
            onChange={(v) => patch("accessToken", v)}
            placeholder="填写 Access Token"
          />
        </Row>
        <Row label="Refresh Token" fieldId="refresh-token">
          <SecretInput
            id="refresh-token"
            value={formState.refreshToken}
            onChange={(v) => patch("refreshToken", v)}
            placeholder="填写 Refresh Token"
          />
        </Row>
      </Section>

      {/* ── Browser ── */}
      <Section
        title="浏览器配置"
        hint="涩花爬虫使用的远程浏览器服务地址，留空则不启用。"
        saveState={browserSave}
        dirty={isDirty(browserKeys)}
        onSave={() => saveSection(browserSave, browserKeys)}
      >
        <Row label="远程 Selenium" hint="填写 host，代码自动拼接 /wd/hub" fieldId="selenium-url">
          <Input
            id="selenium-url"
            value={formState.remoteSeleniumUrl}
            onChange={(e) => patch("remoteSeleniumUrl", e.target.value)}
            placeholder="http://selenium:4444"
          />
        </Row>
        <Row label="FlareSolverr" hint="填写 host，代码自动拼接 /v1" fieldId="flaresolverr-url">
          <Input
            id="flaresolverr-url"
            value={formState.flareSolverrUrl}
            onChange={(e) => patch("flareSolverrUrl", e.target.value)}
            placeholder="http://flaresolverr:8191"
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
  dirty,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
  onSave?: () => void;
  saveState?: SectionSaveState;
  dirty?: boolean;
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
            <Button
              size="sm"
              variant={dirty ? "primary" : "secondary"}
              onClick={onSave}
              loading={saveState.mutation.isPending}
            >
              <Save className="h-3.5 w-3.5" />
              <span>{saveState.justSaved ? "已保存" : saveState.label}</span>
            </Button>
            {saveState.testResult ? (
              <p className={cn(
                "max-w-44 break-words text-right text-xs",
                saveState.testResult.ok ? "text-emerald-600" : "text-rose-500",
              )}>
                {saveState.testResult.message}
              </p>
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

function Row({
  label,
  hint,
  fieldId,
  children,
}: {
  label: string;
  hint?: string;
  fieldId?: string;
  children: ReactNode;
}) {
  return (
    <div className="config-row">
      <div className="config-row-label">
        <label
          className="text-sm font-medium"
          htmlFor={fieldId}
        >
          {label}
        </label>
        {hint ? <p className="mt-1 break-words text-xs leading-snug text-muted-foreground">{hint}</p> : null}
      </div>
      <div className="config-row-control">{children}</div>
    </div>
  );
}

function SecretInput({
  id,
  value,
  onChange,
  placeholder,
}: {
  id?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative flex w-full min-w-0 items-center">
      <Input
        id={id}
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pr-9"
      />
      <button
        type="button"
        onClick={() => setShow((v) => !v)}
        className="absolute right-2.5 flex h-5 w-5 items-center justify-center rounded text-muted-foreground transition hover:text-foreground"
        aria-label={show ? "隐藏" : "显示"}
        tabIndex={-1}
      >
        {show ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
      </button>
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
