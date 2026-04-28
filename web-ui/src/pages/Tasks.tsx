import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Trash2 } from "lucide-react";

import { tasksApi } from "../api/queries";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { errorMessage, formatDateTime } from "../lib/utils";

export function Tasks() {
  const queryClient = useQueryClient();
  const tasks = useQuery({ queryKey: ["tasks"], queryFn: tasksApi.list });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["tasks"] });
  const retry = useMutation({ mutationFn: tasksApi.retry, onSuccess: refresh });
  const remove = useMutation({ mutationFn: tasksApi.delete, onSuccess: refresh });
  const clear = useMutation({ mutationFn: tasksApi.clear, onSuccess: refresh });

  return (
    <>
      <PageHeader
        title="离线任务"
        description="查看失败重试队列，重新提交或清理待重试任务"
        actions={<Button variant="danger" loading={clear.isPending} onClick={() => clear.mutate()}>清空待重试</Button>}
      />
      <Card>
        {tasks.isPending ? <LoadingState /> : null}
        {tasks.isError ? <ErrorState message={errorMessage(tasks.error)} /> : null}
        {tasks.data?.items.length === 0 ? <EmptyState>暂无离线重试任务</EmptyState> : null}
        {tasks.data?.items.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="border-b border-border text-left text-muted-foreground">
                <tr>
                  <th className="py-2 pr-4 font-medium">标题</th>
                  <th className="py-2 pr-4 font-medium">状态</th>
                  <th className="py-2 pr-4 font-medium">重试</th>
                  <th className="py-2 pr-4 font-medium">创建时间</th>
                  <th className="py-2 pr-4 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {tasks.data.items.map((task) => (
                  <tr key={task.id}>
                    <td className="max-w-2xl py-3 pr-4">
                      <div className="font-medium">{task.title}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{task.save_path || task.magnet || "-"}</div>
                    </td>
                    <td className="py-3 pr-4"><Badge tone={task.is_download ? "success" : "warning"}>{task.is_download ? "已完成" : "待重试"}</Badge></td>
                    <td className="py-3 pr-4">{task.retry_count}</td>
                    <td className="py-3 pr-4 text-muted-foreground">{formatDateTime(task.created_at)}</td>
                    <td className="py-3 pr-4">
                      <div className="flex justify-end gap-2">
                        <Button size="icon" variant="secondary" loading={retry.isPending} onClick={() => retry.mutate(task.id)} aria-label="重试"><RefreshCw className="h-4 w-4" /></Button>
                        <Button size="icon" variant="ghost" loading={remove.isPending} onClick={() => remove.mutate(task.id)} aria-label="删除"><Trash2 className="h-4 w-4" /></Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
    </>
  );
}
