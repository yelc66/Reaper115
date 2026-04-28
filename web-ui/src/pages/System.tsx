import { useQuery } from "@tanstack/react-query";

import { systemApi } from "../api/queries";
import { Badge, Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { errorMessage } from "../lib/utils";

export function System() {
  const status = useQuery({
    queryKey: ["system", "status"],
    queryFn: systemApi.status,
    refetchInterval: 10000,
  });

  return (
    <>
      <PageHeader title="系统状态" description="查看 OpenAPI、Token、路径等运行状态" />
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-base font-semibold">运行状态</h2>
          {status.isPending ? <LoadingState /> : null}
          {status.isError ? <ErrorState message={errorMessage(status.error)} /> : null}
          {status.data ? (
            <div className="space-y-3 text-sm">
              <StatusLine label="115 OpenAPI" active={status.data.openapi_ready} />
              <StatusLine label="Token 文件" active={status.data.token_file_exists} />
              <StatusLine
                label="爬虫状态"
                active={status.data.crawl_running}
                activeText="运行中"
                inactiveText="空闲"
              />
              <StatusLine
                label="调试模式"
                active={status.data.debug_mode}
                activeText="开启"
                inactiveText="关闭"
              />
            </div>
          ) : null}
        </Card>

        <Card>
          <h2 className="mb-4 text-base font-semibold">路径</h2>
          {status.isPending ? <LoadingState /> : null}
          <div className="space-y-3 text-xs">
            {Object.entries(status.data?.paths ?? {}).map(([key, value]) => (
              <div key={key}>
                <div className="mb-0.5 text-muted-foreground">{key}</div>
                <div className="break-all font-mono">{value}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}

function StatusLine({
  label,
  active,
  activeText = "正常",
  inactiveText = "异常",
}: {
  label: string;
  active: boolean;
  activeText?: string;
  inactiveText?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <Badge tone={active ? "success" : "warning"}>{active ? activeText : inactiveText}</Badge>
    </div>
  );
}
