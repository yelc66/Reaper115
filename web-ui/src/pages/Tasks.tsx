import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, RefreshCw, Trash2 } from "lucide-react";

import { tasksApi } from "../api/queries";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
} from "../components/ui";
import { errorMessage, formatDateTime } from "../lib/utils";

export function Tasks() {
  const queryClient = useQueryClient();
  const [confirmClear, setConfirmClear] = useState(false);

  const tasksQuery = useQuery({ queryKey: ["tasks"], queryFn: tasksApi.list });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["tasks"] });
  const retryMutation = useMutation({ mutationFn: tasksApi.retry, onSuccess: refresh });
  const removeMutation = useMutation({ mutationFn: tasksApi.delete, onSuccess: refresh });
  const clearMutation = useMutation({
    mutationFn: tasksApi.clear,
    onSuccess: refresh,
  });

  const items = tasksQuery.data?.items ?? [];
  const pending = items.filter((t) => !t.isDownload).length;
  const done = items.filter((t) => t.isDownload).length;

  return (
    <>
      <PageHeader
        title="重试任务"
        description="查看等待重试的失败任务，可单独重试或丢弃。"
        actions={
          <Button
            variant="danger"
            size="sm"
            loading={clearMutation.isPending}
            disabled={items.length === 0}
            onClick={() => setConfirmClear(true)}
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>清空任务</span>
          </Button>
        }
      />

      {/* Stat cards */}
      <div className="mb-4 grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard
          label="待处理"
          value={String(pending)}
          icon={<Clock className="h-8 w-8" />}
          tone="warning"
        />
        <StatCard
          label="已完成"
          value={String(done)}
          icon={<RefreshCw className="h-8 w-8" />}
          tone="success"
        />
        <StatCard
          label="队列总数"
          value={String(items.length)}
          icon={<Clock className="h-8 w-8" />}
          tone="primary"
        />
        <StatCard
          label="最大重试"
          value="6"
          icon={<Trash2 className="h-8 w-8" />}
          tone="default"
        />
      </div>

      <Card>
        {tasksQuery.isPending ? <LoadingState /> : null}
        {tasksQuery.isError ? <ErrorState message={errorMessage(tasksQuery.error)} /> : null}
        {items.length === 0 && !tasksQuery.isPending ? (
          <EmptyState>
            <p>暂无待重试任务</p>
            <p className="mt-1 text-xs">失败的离线下载会自动加入队列，调度器每 12 小时重试一次，最多 6 次。</p>
          </EmptyState>
        ) : null}
        {items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">标题</th>
                  <th className="w-28 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">状态</th>
                  <th className="w-20 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">重试</th>
                  <th className="w-40 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">创建时间</th>
                  <th className="w-28 pb-2 text-right text-[13px] font-medium text-muted-foreground" />
                </tr>
              </thead>
              <tbody>
                {items.map((task) => (
                  <tr key={task.id} className="border-t border-border/60">
                    <td className="max-w-sm py-3 pr-4">
                      <div className="title-clamp font-medium leading-snug">{task.title}</div>
                      <div className="text-cell mt-0.5 font-mono text-xs text-muted-foreground">
                        {task.savePath || task.magnet || "—"}
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      <Badge tone={task.isDownload ? "success" : "warning"}>
                        {task.isDownload ? "已完成" : "待处理"}
                      </Badge>
                    </td>
                    <td className="py-3 pr-4">
                      <span className={task.retryCount >= 5 ? "font-mono text-rose-600" : "font-mono"}>
                        {task.retryCount}/6
                      </span>
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-muted-foreground">
                      {formatDateTime(task.createdAt)}
                    </td>
                    <td className="py-3">
                      <div className="flex justify-end gap-1.5">
                        <Button
                          size="sm"
                          variant="secondary"
                          loading={retryMutation.isPending}
                          onClick={() => retryMutation.mutate(task.id)}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          <span>重试</span>
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          loading={removeMutation.isPending}
                          onClick={() => removeMutation.mutate(task.id)}
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
        ) : null}
      </Card>

      <ConfirmDialog
        open={confirmClear}
        title="清空所有任务"
        message={`将删除队列中全部 ${items.length} 条任务（包括待处理和已完成），此操作不可撤销。`}
        confirmLabel="确认清空"
        danger
        onConfirm={() => {
          setConfirmClear(false);
          clearMutation.mutate();
        }}
        onCancel={() => setConfirmClear(false)}
      />
    </>
  );
}
