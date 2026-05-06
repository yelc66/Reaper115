import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Play, Square } from "lucide-react";

import { API_BASE_URL, getStoredAuthKey } from "../api/client";
import { crawlApi } from "../api/queries";
import { Badge, Button, Card, ErrorState, PageHeader } from "../components/ui";
import { errorMessage } from "../lib/utils";

type LogItem = { time: string; level: string; message: string };

const PRESETS = [
  { id: "today",     label: "今天" },
  { id: "yesterday", label: "昨天" },
  { id: "7days",     label: "近 7 天" },
] as const;

type PresetId = (typeof PRESETS)[number]["id"];

export function Crawl() {
  const [preset, setPreset] = useState<PresetId>("today");
  const [logs, setLogs] = useState<LogItem[]>([]);
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
      setLogs((current) => [...current.slice(-199), item]);
    });
    return () => source.close();
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [logs]);

  const running = statusQuery.data?.running ?? false;

  function handleRun() {
    triggerMutation.mutate({ mode: preset });
  }

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
              onClick={handleRun}
            >
              <Play className="h-3.5 w-3.5" />
              <span>开始抓取</span>
            </Button>
          )
        }
      />

      {/* Date preset selector */}
      <Card className="mb-4">
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
        {triggerMutation.isError ? (
          <div className="mt-3">
            <ErrorState message={errorMessage(triggerMutation.error)} />
          </div>
        ) : null}
      </Card>

      {/* Live log */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">实时日志</h2>
          <Badge tone={running ? "info" : "default"}>
            {running ? "推送中 · SSE" : "空闲"}
          </Badge>
        </div>
        <div ref={logRef} className="log-pane">
          {logs.length === 0 ? (
            <div className="log-empty">- 等待日志 -</div>
          ) : null}
          {logs.map((item, index) => (
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
