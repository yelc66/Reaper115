import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Play, Radio } from "lucide-react";

import { API_BASE_URL } from "../api/client";
import { crawlApi } from "../api/queries";
import { Badge, Button, Card, ErrorState, PageHeader } from "../components/ui";
import { errorMessage } from "../lib/utils";

type LogItem = {
  time: string;
  level: string;
  message: string;
};

const datePresets = [
  { label: "今天", mode: "today" },
  { label: "昨天", mode: "yesterday" },
  { label: "七天", mode: "7days" },
] as const;

export function Crawl() {
  const [crawlMode, setCrawlMode] = useState<(typeof datePresets)[number]["mode"]>("today");
  const [logs, setLogs] = useState<LogItem[]>([]);
  const logContainerRef = useRef<HTMLDivElement | null>(null);
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
    const source = new EventSource(`${API_BASE_URL}/api/crawl/logs`);
    source.addEventListener("log", (event) => {
      const item = JSON.parse((event as MessageEvent).data) as LogItem;
      setLogs((current) => [...current.slice(-199), item]);
    });
    return () => source.close();
  }, []);

  useEffect(() => {
    logContainerRef.current?.scrollTo({ top: logContainerRef.current.scrollHeight });
  }, [logs]);

  return (
    <>
      <PageHeader
        title="爬取控制"
        description="按页面显示时间触发涩花爬虫，并观察后端实时日志"
        actions={
          <Badge tone={statusQuery.data?.running ? "warning" : "success"}>
            {statusQuery.data?.running ? "运行中" : "空闲"}
          </Badge>
        }
      />
      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Card>
          <h2 className="mb-4 text-base font-semibold">手动触发</h2>
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              {datePresets.map((preset) => (
                <Button
                  key={preset.mode}
                  type="button"
                  variant={preset.mode === crawlMode ? "primary" : "secondary"}
                  size="sm"
                  onClick={() => setCrawlMode(preset.mode)}
                >
                  {preset.label}
                </Button>
              ))}
            </div>
            <Button
              className="w-full"
              loading={triggerMutation.isPending}
              disabled={statusQuery.data?.running}
              onClick={() => triggerMutation.mutate({ mode: crawlMode })}
            >
              <Play className="h-4 w-4" />
              开始爬取
            </Button>
            {triggerMutation.isError ? <ErrorState message={errorMessage(triggerMutation.error)} /> : null}
          </div>
        </Card>
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">实时日志</h2>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Radio className="h-4 w-4" />
              SSE
            </div>
          </div>
          <div
            ref={logContainerRef}
            className="h-[560px] overflow-auto rounded-md bg-slate-950 p-3 font-mono text-xs text-slate-100"
          >
            {logs.length === 0 ? <div className="text-slate-400">等待日志...</div> : null}
            {logs.map((item, index) => (
              <div key={`${item.time}-${index}`} className="mb-1 grid grid-cols-[150px_72px_1fr] gap-2">
                <span className="text-slate-400">{item.time}</span>
                <span
                  className={
                    item.level === "ERROR"
                      ? "text-rose-300"
                      : item.level === "WARNING"
                        ? "text-amber-300"
                        : "text-emerald-300"
                  }
                >
                  {item.level}
                </span>
                <span className="break-words">{item.message}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
