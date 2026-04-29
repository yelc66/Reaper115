import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Search, Trash2 } from "lucide-react";

import { sehuaApi } from "../api/queries";
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, PageHeader, Select } from "../components/ui";
import { errorMessage, formatDateTime } from "../lib/utils";

const PAGE_SIZE = 20;

export function SehuaData() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [section, setSection] = useState("");
  const [status, setStatus] = useState("");
  const [keyword, setKeyword] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const sehuaQuery = useQuery({
    queryKey: ["sehua", { page, section, status, keyword }],
    queryFn: () => sehuaApi.list({ page, size: PAGE_SIZE, section, status, keyword }),
  });

  const invalidateSehuaQueries = () => queryClient.invalidateQueries({ queryKey: ["sehua"] });
  const downloadMutation = useMutation({ mutationFn: sehuaApi.download, onSuccess: invalidateSehuaQueries });
  const batchDownloadMutation = useMutation({
    mutationFn: sehuaApi.batchDownload,
    onSuccess: () => {
      setSelectedIds([]);
      invalidateSehuaQueries();
    },
  });
  const removeMutation = useMutation({ mutationFn: sehuaApi.delete, onSuccess: invalidateSehuaQueries });

  const totalPages = Math.max(1, Math.ceil((sehuaQuery.data?.total ?? 0) / PAGE_SIZE));
  const sections = useMemo(
    () => Array.from(new Set((sehuaQuery.data?.items ?? []).map((item) => item.sectionName))).filter(Boolean),
    [sehuaQuery.data],
  );

  return (
    <>
      <PageHeader
        title="涩花数据"
        description="筛选已抓取资源，提交单条或批量离线任务"
        actions={
          <Button
            loading={batchDownloadMutation.isPending}
            disabled={selectedIds.length === 0}
            onClick={() => batchDownloadMutation.mutate(selectedIds)}
          >
            <Download className="h-4 w-4" />
            批量离线
          </Button>
        }
      />
      <Card className="mb-4">
        <div className="grid gap-3 md:grid-cols-[1fr_160px_140px_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="标题、番号或磁力关键词"
              value={keyword}
              onChange={(event) => {
                setKeyword(event.target.value);
                setPage(1);
              }}
            />
          </div>
          <Select
            value={section}
            onChange={(event) => {
              setSection(event.target.value);
              setPage(1);
            }}
          >
            <option value="">全部版块</option>
            {sections.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </Select>
          <Select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">全部状态</option>
            <option value="0">待处理</option>
            <option value="1">已离线</option>
          </Select>
          <Button
            variant="secondary"
            onClick={() => {
              setKeyword("");
              setSection("");
              setStatus("");
              setPage(1);
            }}
          >
            重置
          </Button>
        </div>
      </Card>
      {sehuaQuery.isPending ? <LoadingState /> : null}
      {sehuaQuery.isError ? <ErrorState message={errorMessage(sehuaQuery.error)} /> : null}
      {sehuaQuery.data ? (
        <Card>
          {sehuaQuery.data.items.length === 0 ? <EmptyState>没有匹配的资源</EmptyState> : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="border-b border-border text-left text-muted-foreground">
                  <tr>
                    <th className="w-10 py-2 pr-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.length === sehuaQuery.data.items.length}
                        onChange={(event) =>
                          setSelectedIds(event.target.checked ? sehuaQuery.data.items.map((item) => item.id) : [])
                        }
                      />
                    </th>
                    <th className="py-2 pr-4 font-medium">标题</th>
                    <th className="py-2 pr-4 font-medium">版块</th>
                    <th className="py-2 pr-4 font-medium">大小</th>
                    <th className="py-2 pr-4 font-medium">状态</th>
                    <th className="py-2 pr-4 font-medium">日期</th>
                    <th className="py-2 pr-4 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {sehuaQuery.data.items.map((item) => (
                    <tr key={item.id}>
                      <td className="py-3 pr-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(item.id)}
                          onChange={(event) =>
                            setSelectedIds((currentIds) =>
                              event.target.checked
                                ? [...currentIds, item.id]
                                : currentIds.filter((id) => id !== item.id),
                            )
                          }
                        />
                      </td>
                      <td className="max-w-xl py-3 pr-4">
                        <div className="font-medium">{item.title}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{item.avNumber || item.savePath || "-"}</div>
                      </td>
                      <td className="py-3 pr-4">{item.sectionName}</td>
                      <td className="py-3 pr-4">{item.size || "-"}</td>
                      <td className="py-3 pr-4">
                        <Badge tone={item.isDownload ? "success" : "warning"}>
                          {item.isDownload ? "已离线" : "待处理"}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">{formatDateTime(item.publishDate)}</td>
                      <td className="py-3 pr-4">
                        <div className="flex justify-end gap-2">
                          <Button
                            size="icon"
                            variant="secondary"
                            loading={downloadMutation.isPending}
                            onClick={() => downloadMutation.mutate(item.id)}
                            aria-label="离线"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            loading={removeMutation.isPending}
                            onClick={() => removeMutation.mutate(item.id)}
                            aria-label="删除"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <span>
              共 {sehuaQuery.data.total} 条，第 {page} / {totalPages} 页
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
                上一页
              </Button>
              <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage((value) => value + 1)}>
                下一页
              </Button>
            </div>
          </div>
        </Card>
      ) : null}
    </>
  );
}
