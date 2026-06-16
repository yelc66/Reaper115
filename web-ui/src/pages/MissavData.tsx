import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bug, ChevronLeft, ChevronRight, Download, Search, Trash2, Wand2 } from "lucide-react";

import { API_BASE_URL, getStoredAuthKey } from "../api/client";
import { missavApi } from "../api/queries";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  PageHeader,
  Select,
} from "../components/ui";
import { errorMessage, formatDateTime } from "../lib/utils";

const PAGE_SIZE = 20;

type LogItem = { time: string; level: string; message: string };

export function MissavData() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [section, setSection] = useState("");
  const [status, setStatus] = useState("");
  const [keyword, setKeyword] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const logRef = useRef<HTMLDivElement | null>(null);

  const missavQuery = useQuery({
    queryKey: ["missav", { page, section, status, keyword }],
    queryFn: () => missavApi.list({ page, size: PAGE_SIZE, section, status, keyword }),
  });

  const listsQuery = useQuery({
    queryKey: ["missav", "lists"],
    queryFn: missavApi.lists,
  });

  const processStatusQuery = useQuery({
    queryKey: ["missav", "process-status"],
    queryFn: missavApi.processStatus,
    refetchInterval: 3000,
  });

  const crawlStatusQuery = useQuery({
    queryKey: ["missav", "crawl-status"],
    queryFn: missavApi.crawlStatus,
    refetchInterval: 3000,
  });

  const processing = processStatusQuery.data?.running ?? false;
  const crawling = crawlStatusQuery.data?.running ?? false;

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["missav"] });
  const downloadMutation = useMutation({ mutationFn: missavApi.download, onSuccess: invalidate });
  const postProcessMutation = useMutation({
    mutationFn: missavApi.postProcess,
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["missav", "process-status"] });
    },
  });
  const batchPostProcessMutation = useMutation({
    mutationFn: missavApi.batchPostProcess,
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["missav", "process-status"] });
    },
  });
  const batchDownloadMutation = useMutation({
    mutationFn: missavApi.batchDownload,
    onSuccess: () => { setSelectedIds([]); invalidate(); },
  });
  const triggerMutation = useMutation({
    mutationFn: missavApi.trigger,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["missav", "crawl-status"] }),
  });
  const removeMutation = useMutation({ mutationFn: missavApi.delete, onSuccess: invalidate });
  const batchDeleteMutation = useMutation({
    mutationFn: missavApi.batchDelete,
    onSuccess: () => { setSelectedIds([]); invalidate(); },
  });

  // SSE log stream — reuse the same /api/crawl/logs endpoint
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

  const totalPages = Math.max(1, Math.ceil((missavQuery.data?.total ?? 0) / PAGE_SIZE));
  const sections = listsQuery.data ?? [];

  const items = missavQuery.data?.items ?? [];
  const allSelected = items.length > 0 && selectedIds.length === items.length;

  return (
    <>
      <PageHeader
        title="missav 数据"
        description="查看 missav 榜单爬虫入库的资源，支持筛选、检查和批量导出到离线下载。"
        actions={
          <>
            <Button
              size="sm"
              loading={triggerMutation.isPending}
              disabled={crawling}
              onClick={() => triggerMutation.mutate()}
            >
              <Bug className="h-3.5 w-3.5" />
              <span>{crawling ? "抓取中…" : "开始抓取"}</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              loading={batchDeleteMutation.isPending}
              disabled={selectedIds.length === 0}
              onClick={() => batchDeleteMutation.mutate(selectedIds)}
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>删除所选</span>
            </Button>
            <Button
              size="sm"
              loading={batchDownloadMutation.isPending}
              disabled={selectedIds.length === 0}
              onClick={() => batchDownloadMutation.mutate(selectedIds)}
            >
              <Download className="h-3.5 w-3.5" />
              <span>导出所选</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              loading={batchPostProcessMutation.isPending}
              disabled={processing}
              onClick={() => batchPostProcessMutation.mutate()}
            >
              <Wand2 className="h-3.5 w-3.5" />
              <span>{processing ? "处理中…" : "一键后处理"}</span>
            </Button>
          </>
        }
      />

      {/* Filter bar */}
      <Card className="mb-4 flex flex-wrap items-center gap-3 p-3">
        <div className="relative min-w-0 flex-1" style={{ flexBasis: 280 }}>
          <Search className="pointer-events-none absolute left-3 top-2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="搜索标题、番号、磁链..."
            value={keyword}
            onChange={(e) => { setKeyword(e.target.value); setPage(1); }}
          />
        </div>
        <Select
          className="w-40"
          value={section}
          onChange={(e) => { setSection(e.target.value); setPage(1); }}
        >
          <option value="">全部榜单</option>
          {sections.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </Select>
        <Select
          className="w-36"
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
        >
          <option value="">全部状态</option>
          <option value="2">已完成</option>
          <option value="1">待后处理</option>
          <option value="0">待下载</option>
        </Select>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => { setKeyword(""); setSection(""); setStatus(""); setPage(1); }}
        >
          <span>重置</span>
        </Button>
      </Card>

      {missavQuery.isPending ? <LoadingState /> : null}
      {missavQuery.isError ? <ErrorState message={errorMessage(missavQuery.error)} /> : null}

      {missavQuery.data ? (
        <Card className="mb-4">
          {items.length === 0 ? (
            <EmptyState>没有匹配的资源</EmptyState>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="w-8 pb-2 pr-3 text-left">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={(e) => setSelectedIds(e.target.checked ? items.map((i) => i.id) : [])}
                      />
                    </th>
                    <th className="w-20 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">ID</th>
                    <th className="pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">标题</th>
                    <th className="w-24 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">大小</th>
                    <th className="w-28 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">发布时间</th>
                    <th className="w-24 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">状态</th>
                    <th className="w-20 pb-2 text-right text-[13px] font-medium text-muted-foreground" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-border/60">
                      <td className="py-3 pr-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(item.id)}
                          onChange={(e) =>
                            setSelectedIds((ids) =>
                              e.target.checked ? [...ids, item.id] : ids.filter((id) => id !== item.id),
                            )
                          }
                        />
                      </td>
                      <td className="py-3 pr-4 font-mono text-muted-foreground">#{item.id}</td>
                      <td className="max-w-sm py-3 pr-4">
                        <div className="text-cell font-medium leading-snug">{item.title}</div>
                        <div className="text-cell mt-0.5 font-mono text-xs text-muted-foreground">
                          {item.avNumber || item.savePath || "—"}
                        </div>
                      </td>
                      <td className="py-3 pr-4 font-mono text-[12px]">{item.size || "—"}</td>
                      <td className="py-3 pr-4 font-mono text-xs text-muted-foreground">
                        {formatDateTime(item.publishDate)}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge
                          tone={item.isDownload === 2 ? "success" : item.isDownload === 1 ? "warning" : "default"}
                        >
                          {item.isDownload === 2 ? "已完成" : item.isDownload === 1 ? "待后处理" : "待下载"}
                        </Badge>
                      </td>
                      <td className="py-3 text-right">
                        <div className="flex justify-end gap-1.5">
                          {item.isDownload === 0 && (
                            <Button
                              size="icon"
                              variant="secondary"
                              loading={downloadMutation.isPending}
                              onClick={() => downloadMutation.mutate(item.id)}
                              aria-label="提交离线"
                              title="提交离线"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          {item.isDownload === 1 && (
                            <Button
                              size="icon"
                              variant="secondary"
                              loading={postProcessMutation.isPending}
                              disabled={processing}
                              onClick={() => postProcessMutation.mutate(item.id)}
                              aria-label="去广告并重命名"
                              title="去广告并重命名"
                            >
                              <Wand2 className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <Button
                            size="icon"
                            variant="ghost"
                            loading={removeMutation.isPending}
                            onClick={() => removeMutation.mutate(item.id)}
                            aria-label="删除"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-xs text-muted-foreground">
              第 {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, missavQuery.data.total)} 条，共{" "}
              {missavQuery.data.total} 条
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                variant="ghost"
                size="icon"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="secondary" size="sm">{page}</Button>
              {page < totalPages && (
                <Button variant="ghost" size="sm" onClick={() => setPage((p) => p + 1)}>
                  {page + 1}
                </Button>
              )}
              {totalPages > page + 1 && (
                <Button variant="ghost" size="sm" className="text-muted-foreground">…</Button>
              )}
              {totalPages > page + 1 && (
                <Button variant="ghost" size="sm" onClick={() => setPage(totalPages)}>
                  {totalPages}
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      {/* Live log panel */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">后处理日志</h2>
          <div className="flex items-center gap-2">
            {logs.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setLogs([])}>
                清空
              </Button>
            )}
            <Badge tone={processing ? "info" : "default"}>
              {processing ? "处理中 · SSE" : "空闲"}
            </Badge>
          </div>
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
          {processing && (
            <div className="log-line">
              <span className="log-time" />
              <span className="log-info">INFO </span>
              <span className="animate-pulse">▌</span>
            </div>
          )}
          {!processing && logs.length > 0 && (
            <div className="log-empty mt-2">- 日志流已暂停 -</div>
          )}
        </div>
      </Card>
    </>
  );
}
