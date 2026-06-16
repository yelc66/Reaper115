import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { PauseCircle, Play, PlayCircle, Square } from "lucide-react";

import { API_BASE_URL, getStoredAuthKey } from "../api/client";
import { crawlApi } from "../api/queries";
import { Badge, Button, Card, ErrorState, PageHeader } from "../components/ui";
import { errorMessage } from "../lib/utils";

type LogLevel = "ALL" | "INFO" | "WARNING" | "ERROR";
type LogItem = { time: string; level: string; message: string };

const PRESETS = [
  { id: "today",     label: "今天" },
  { id: "yesterday", label: "昨天" },
  { id: "7days",     label: "近 7 天" },
] as const;

type PresetId = (typeof PRESETS)[number]["id"];

const PRESET_LABEL: Record<PresetId, string> = {
  today: "今天",
  yesterday: "昨天",
  "7days": "近 7 天",
};

export function Crawl() {
  const [preset, setPreset] = useState<PresetId>("today");
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [logLevel, setLogLevel] = useState<LogLevel>("ALL");
  const [autoscroll, setAutoscroll] = useState(true);
  const logRef = useRef<HTMLDivElement | null>(null);

  const statusQuery = useQuery({
    queryKey: ["crawl", "status"],
    queryFn: crawlApi.status,
    refetchInterval: 3000,
  });
  const triggerMutation = useMutation({
    mutationFn: crawlApi.trigger,
    onSuccess: () => statusQuery.refetch(),
  });

  useEffect(() => {
    const authKey = getStoredAuthKey();
    const url = authKey
      ? `${API_BASE_URL}/api/crawl/logs?key=${encodeURIComponent(authKey)}`
      : `${API_BASE_URL}/api/crawl/logs`;
    const source = new EventSource(url);
    source.addEventListener("log", (event) => {
      const item = JSON.parse((event as MessageEvent).data) as LogItem;
      setLogs((current) => [...current.slice(-299), item]);
    });
    return () => source.close();
  }, []);

  useEffect(() => {
    if (autoscroll) {
      logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
    }
  }, [logs, autoscroll]);

  const running = statusQuery.data?.running ?? false;

  const filteredLogs = useMemo(() => {
    if (logLevel === "ALL") return logs;
    if (logLevel === "ERROR") return logs.filter((l) => l.level === "ERROR" || l.level === "CRITICAL");
    return logs.filter((l) => l.level === logLevel);
  }, [logs, logLevel]);

  const errorCount = useMemo(
    () => logs.filter((l) => l.level === "ERROR" || l.level === "CRITICAL").length,
    [logs],
  );

  return (
    <>
      <PageHeader
        title="手动抓取"
        description="按预设时间范围触发一次抓取，日期基于来源帖子的发布时间。"
        actions={
          running ? (
            <Button variant="danger" size="sm" disabled>
              <Square className="h-3.5 w-3.5" />
              <span>运行中</span>
            </Button>
          ) : (
            <Button
              size="sm"
              loading={triggerMutation.isPending}
              disabled={running}
              onClick={() => triggerMutation.mutate({ mode: preset })}
            >
              <Play className="h-3.5 w-3.5" />
              <span>开始抓取 · {PRESET_LABEL[preset]}</span>
            </Button>
          )
        }
      />

      {/* Date preset selector */}
      <Card className="mb-4">
        <div className="mb-3 text-xs font-medium text-muted-foreground">选择抓取范围</div>
        <div className="flex flex-wrap items-center gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setPreset(p.id)}
              className={
                preset === p.id
                  ? "inline-flex h-7 max-w-full items-center justify-center gap-2 overflow-hidden rounded-md bg-primary px-2.5 text-xs font-medium text-white shadow-[var(--shadow-cta)] transition-all"
                  : "inline-flex h-7 max-w-full items-center justify-center gap-2 overflow-hidden rounded-md border border-[var(--glass-border)] bg-white/58 px-2.5 text-xs font-medium text-foreground shadow-[var(--shadow-card-soft)] backdrop-blur-xl transition-all hover:-translate-y-0.5 hover:bg-white/72"
              }
            >
              <span className="truncate">{p.label}</span>
            </button>
          ))}
        </div>
        {/* Current selection summary */}
        {!running && (
          <p className="mt-3 text-[13px] text-muted-foreground">
            点击「开始抓取」将爬取<strong className="text-foreground">「{PRESET_LABEL[preset]}」</strong>发布的帖子并写入数据库。
          </p>
        )}
        {running && (
          <p className="mt-3 text-[13px] text-primary">
            抓取正在运行，请等待完成后再次触发。
          </p>
        )}
        {triggerMutation.isError ? (
          <div className="mt-3">
            <ErrorState message={errorMessage(triggerMutation.error)} />
          </div>
        ) : null}
      </Card>

      {/* Live log */}
      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold">实时日志</h2>
          <Badge tone={running ? "info" : "default"}>
            {running ? "推送中 · SSE" : "空闲"}
          </Badge>
          {logs.length > 0 && (
            <span className="text-xs text-muted-foreground">{logs.length} 条</span>
          )}
          {errorCount > 0 && (
            <Badge tone="danger">{errorCount} 错误</Badge>
          )}
          <div className="ml-auto flex items-center gap-2">
            <select
              className="h-7 rounded-md border border-[var(--glass-border)] bg-white/62 px-2 text-xs text-foreground outline-none focus:border-primary/60"
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value as LogLevel)}
            >
              <option value="ALL">全部级别</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARN</option>
              <option value="ERROR">ERROR</option>
            </select>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setAutoscroll((v) => !v)}
              title={autoscroll ? "暂停自动滚动" : "恢复自动滚动"}
            >
              {autoscroll
                ? <PauseCircle className="h-3.5 w-3.5" />
                : <PlayCircle className="h-3.5 w-3.5" />}
              <span>{autoscroll ? "暂停滚动" : "自动滚动"}</span>
            </Button>
            {logs.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setLogs([])}>
                清空
              </Button>
            )}
          </div>
        </div>
        <div ref={logRef} className="log-pane">
          {filteredLogs.length === 0 ? (
            <div className="log-empty">
              {logs.length === 0 ? "- 等待日志 -" : "- 没有符合筛选条件的日志 -"}
            </div>
          ) : null}
          {filteredLogs.map((item, index) => (
            <div key={`${item.time}-${index}`} className="log-line">
              <span className="log-time">{item.time}</span>
              <span
                className={
                  item.level === "ERROR" || item.level === "CRITICAL"
                    ? "log-error"
                    : item.level === "WARNING"
                      ? "log-warn"
                      : "log-info"
                }
              >
                {item.level.padEnd(5)}
              </span>
              <span className="text-cell">{item.message}</span>
            </div>
          ))}
          {running && (
            <div className="log-line">
              <span className="log-time" />
              <span className="log-info">INFO </span>
              <span className="animate-pulse">▌</span>
            </div>
          )}
          {!running && logs.length > 0 && (
            <div className="log-empty mt-2">- 日志流已暂停 -</div>
          )}
        </div>
      </Card>
    </>
  );
}
