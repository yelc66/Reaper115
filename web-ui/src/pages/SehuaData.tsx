import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bug, ChevronLeft, ChevronRight, Download, PauseCircle, PlayCircle, Search, Trash2, Wand2 } from "lucide-react";

import { API_BASE_URL, getStoredAuthKey } from "../api/client";
import { crawlApi, sehuaApi } from "../api/queries";
import type { SehuaItem } from "../api/models";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  Drawer,
  DrawerField,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  PageHeader,
  Select,
} from "../components/ui";
import { errorMessage, formatDateTime } from "../lib/utils";

const PAGE_SIZE = 20;

type LogLevel = "ALL" | "INFO" | "WARNING" | "ERROR";
type LogItem = { time: string; level: string; message: string };

const CRAWL_PRESETS = [
  { id: "today",     label: "今天" },
  { id: "yesterday", label: "昨天" },
  { id: "7days",     label: "近 7 天" },
] as const;
type PresetId = (typeof CRAWL_PRESETS)[number]["id"];

function statusLabel(v: number) {
  return v === 2 ? "已完成" : v === 1 ? "待后处理" : "待下载";
}
function statusTone(v: number): "success" | "warning" | "default" {
  return v === 2 ? "success" : v === 1 ? "warning" : "default";
}

export function SehuaData() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [section, setSection] = useState("");
  const [status, setStatus] = useState("");
  const [keyword, setKeyword] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [logLevel, setLogLevel] = useState<LogLevel>("ALL");
  const [autoscroll, setAutoscroll] = useState(true);
  const [drawerItem, setDrawerItem] = useState<SehuaItem | null>(null);
  const [confirmPostProcess, setConfirmPostProcess] = useState(false);
  const [crawlPreset, setCrawlPreset] = useState<PresetId>("today");
  const logRef = useRef<HTMLDivElement | null>(null);

  const sehuaQuery = useQuery({
    queryKey: ["sehua", { page, section, status, keyword }],
    queryFn: () => sehuaApi.list({ page, size: PAGE_SIZE, section, status, keyword }),
  });

  const processStatusQuery = useQuery({
    queryKey: ["sehua", "process-status"],
    queryFn: sehuaApi.processStatus,
    refetchInterval: 3000,
  });

  const processing = processStatusQuery.data?.running ?? false;

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["sehua"] });
  const downloadMutation = useMutation({ mutationFn: sehuaApi.download, onSuccess: invalidate });
  const postProcessMutation = useMutation({
    mutationFn: sehuaApi.postProcess,
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["sehua", "process-status"] });
    },
  });
  const batchPostProcessMutation = useMutation({
    mutationFn: sehuaApi.batchPostProcess,
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["sehua", "process-status"] });
    },
  });
  const batchDownloadMutation = useMutation({
    mutationFn: sehuaApi.batchDownload,
    onSuccess: () => { setSelectedIds([]); invalidate(); },
  });
  const removeMutation = useMutation({ mutationFn: sehuaApi.delete, onSuccess: invalidate });
  const batchDeleteMutation = useMutation({
    mutationFn: sehuaApi.batchDelete,
    onSuccess: () => { setSelectedIds([]); invalidate(); },
  });

  const crawlStatusQuery = useQuery({
    queryKey: ["crawl", "status"],
    queryFn: crawlApi.status,
    refetchInterval: 3000,
  });
  const crawlMutation = useMutation({
    mutationFn: crawlApi.trigger,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["crawl", "status"] }),
  });
  const crawling = crawlStatusQuery.data?.running ?? false;

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

  const totalPages = Math.max(1, Math.ceil((sehuaQuery.data?.total ?? 0) / PAGE_SIZE));
  const sections = useMemo(
    () => Array.from(new Set((sehuaQuery.data?.items ?? []).map((item) => item.sectionName))).filter(Boolean),
    [sehuaQuery.data],
  );

  const items = sehuaQuery.data?.items ?? [];
  const allSelected = items.length > 0 && selectedIds.length === items.length;

  const pendingCount = useMemo(() => items.filter((i) => i.isDownload === 1).length, [items]);

  const filteredLogs = useMemo(() => {
    if (logLevel === "ALL") return logs;
    if (logLevel === "ERROR") return logs.filter((l) => l.level === "ERROR" || l.level === "CRITICAL");
    return logs.filter((l) => l.level === logLevel);
  }, [logs, logLevel]);

  const closeDrawer = useCallback(() => setDrawerItem(null), []);

  return (
    <>
      <PageHeader
        title="涩花数据"
        description="查看爬虫入库的帖子，支持筛选、检查和批量导出到离线下载。"
        actions={
          <>
            {/* Crawl preset selector + trigger */}
            <select
              className="h-7 rounded-md border border-[var(--glass-border)] bg-white/62 px-2 text-xs text-foreground outline-none focus:border-primary/60"
              value={crawlPreset}
              onChange={(e) => setCrawlPreset(e.target.value as PresetId)}
              disabled={crawling}
            >
              {CRAWL_PRESETS.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
            <Button
              size="sm"
              loading={crawlMutation.isPending}
              disabled={crawling}
              onClick={() => crawlMutation.mutate({ mode: crawlPreset })}
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
              <span>删除所选 {selectedIds.length > 0 ? `(${selectedIds.length})` : ""}</span>
            </Button>
            <Button
              size="sm"
              loading={batchDownloadMutation.isPending}
              disabled={selectedIds.length === 0}
              onClick={() => batchDownloadMutation.mutate(selectedIds)}
            >
              <Download className="h-3.5 w-3.5" />
              <span>导出所选 {selectedIds.length > 0 ? `(${selectedIds.length})` : ""}</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              loading={batchPostProcessMutation.isPending}
              disabled={processing}
              onClick={() => setConfirmPostProcess(true)}
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
          <option value="">全部板块</option>
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

      {sehuaQuery.isPending ? <LoadingState /> : null}
      {sehuaQuery.isError ? <ErrorState message={errorMessage(sehuaQuery.error)} /> : null}

      {sehuaQuery.data ? (
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
                    <th className="pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">标题</th>
                    <th className="w-24 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">状态</th>
                    <th className="w-20 pb-2 text-right text-[13px] font-medium text-muted-foreground" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className="cursor-pointer border-t border-border/60 transition-colors hover:bg-black/[0.025]"
                      onClick={() => setDrawerItem(item)}
                    >
                      <td className="py-3 pr-3" onClick={(e) => e.stopPropagation()}>
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
                      <td className="py-3 pr-4">
                        <div className="title-clamp font-medium leading-snug text-foreground">
                          {item.title}
                        </div>
                        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                          {item.avNumber && (
                            <span className="font-mono text-xs text-primary/80">{item.avNumber}</span>
                          )}
                          {item.size && (
                            <span className="font-mono text-xs text-muted-foreground">{item.size}</span>
                          )}
                          {item.sectionName && (
                            <span className="text-xs text-muted-foreground">{item.sectionName}</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge tone={statusTone(item.isDownload)}>
                          {statusLabel(item.isDownload)}
                        </Badge>
                      </td>
                      <td className="py-3 text-right" onClick={(e) => e.stopPropagation()}>
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
              第 {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, sehuaQuery.data.total)} 条，共{" "}
              {sehuaQuery.data.total} 条
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
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold">后处理日志</h2>
          <Badge tone={processing ? "info" : "default"}>
            {processing ? "处理中 · SSE" : "空闲"}
          </Badge>
          {logs.length > 0 && (
            <span className="text-xs text-muted-foreground">{logs.length} 条</span>
          )}
          <div className="ml-auto flex items-center gap-2">
            {/* Level filter */}
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
            {/* Autoscroll toggle */}
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

      {/* Detail drawer */}
      <Drawer
        open={drawerItem !== null}
        onClose={closeDrawer}
        title="资源详情"
      >
        {drawerItem && (
          <>
            <DrawerField label="标题">
              <p className="leading-relaxed">{drawerItem.title}</p>
            </DrawerField>
            <DrawerField label="状态">
              <Badge tone={statusTone(drawerItem.isDownload)}>
                {statusLabel(drawerItem.isDownload)}
              </Badge>
            </DrawerField>
            {drawerItem.avNumber && (
              <DrawerField label="番号">
                <span className="font-mono text-primary">{drawerItem.avNumber}</span>
              </DrawerField>
            )}
            {drawerItem.sectionName && (
              <DrawerField label="板块">{drawerItem.sectionName}</DrawerField>
            )}
            {drawerItem.size && (
              <DrawerField label="大小">
                <span className="font-mono">{drawerItem.size}</span>
              </DrawerField>
            )}
            {drawerItem.publishDate && (
              <DrawerField label="发布时间">
                <span className="font-mono text-xs">{formatDateTime(drawerItem.publishDate)}</span>
              </DrawerField>
            )}
            {drawerItem.savePath && (
              <DrawerField label="保存路径">
                <span className="break-all font-mono text-xs text-muted-foreground">
                  {drawerItem.savePath}
                </span>
              </DrawerField>
            )}
            {drawerItem.magnet && (
              <DrawerField label="磁链">
                <span className="break-all font-mono text-[11px] text-muted-foreground">
                  {drawerItem.magnet}
                </span>
              </DrawerField>
            )}
            {drawerItem.postUrl && (
              <DrawerField label="帖子链接">
                <a
                  href={drawerItem.postUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="break-all text-xs text-primary underline-offset-2 hover:underline"
                >
                  {drawerItem.postUrl}
                </a>
              </DrawerField>
            )}
            <div className="mt-6 flex gap-2">
              {drawerItem.isDownload === 0 && (
                <Button
                  size="sm"
                  loading={downloadMutation.isPending}
                  onClick={() => { downloadMutation.mutate(drawerItem.id); closeDrawer(); }}
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>提交离线</span>
                </Button>
              )}
              {drawerItem.isDownload === 1 && (
                <Button
                  size="sm"
                  variant="secondary"
                  loading={postProcessMutation.isPending}
                  disabled={processing}
                  onClick={() => { postProcessMutation.mutate(drawerItem.id); closeDrawer(); }}
                >
                  <Wand2 className="h-3.5 w-3.5" />
                  <span>去广告并重命名</span>
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                loading={removeMutation.isPending}
                onClick={() => { removeMutation.mutate(drawerItem.id); closeDrawer(); }}
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>删除</span>
              </Button>
            </div>
          </>
        )}
      </Drawer>

      {/* Batch post-process confirm */}
      <ConfirmDialog
        open={confirmPostProcess}
        title="一键后处理"
        message={
          pendingCount > 0
            ? `将对当前页 ${pendingCount} 条「待后处理」资源执行去广告和重命名。确认继续？`
            : "当前页没有「待后处理」状态的资源。仍要执行全量后处理？"
        }
        confirmLabel="开始处理"
        onConfirm={() => {
          setConfirmPostProcess(false);
          batchPostProcessMutation.mutate();
        }}
        onCancel={() => setConfirmPostProcess(false)}
      />
    </>
  );
}
