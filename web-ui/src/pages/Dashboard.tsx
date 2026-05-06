import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CheckCircle2,
  Clock3,
  Cpu,
  Database,
  HardDrive,
  RotateCcw,
  Server,
  Wifi,
} from "lucide-react";
import {
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { dashboardApi, systemApi } from "../api/queries";
import { Badge, Card, ErrorState, LoadingState, PageHeader, StatCard } from "../components/ui";
import { errorMessage, formatDateTime, formatNumber } from "../lib/utils";

const CHART_PALETTE = ["#007AFF", "#34C759", "#FF9500", "#AF52DE", "#5856D6", "#8E8E93"];

export function Dashboard() {
  const statsQuery = useQuery({ queryKey: ["dashboard", "stats"], queryFn: dashboardApi.stats });
  const trendQuery = useQuery({ queryKey: ["dashboard", "trend", 30], queryFn: () => dashboardApi.trend(30) });
  const statusQuery = useQuery({
    queryKey: ["system", "status"],
    queryFn: systemApi.status,
    refetchInterval: 10000,
  });

  if (statsQuery.isPending || trendQuery.isPending) return <LoadingState />;
  if (statsQuery.isError) return <ErrorState message={errorMessage(statsQuery.error)} />;
  if (trendQuery.isError) return <ErrorState message={errorMessage(trendQuery.error)} />;

  return (
    <>
      <PageHeader
        title="仪表盘"
        description="查看系统状态、抓取吞吐和最近活动。"
      />

      {/* ── System + stat cards row ── */}
      <div className="mb-4 grid gap-4 xl:grid-cols-[0.78fr_1.22fr]">
        {/* System status */}
        <Card>
          <h2 className="mb-3 text-base font-semibold">系统状态</h2>
          {statusQuery.isPending ? <LoadingState /> : null}
          {statusQuery.isError ? <ErrorState message={errorMessage(statusQuery.error)} /> : null}
          {statusQuery.data ? (
            <div className="flex flex-col gap-1.5">
              <InsetRow
                icon={<Server className="h-4 w-4" />}
                label="API"
                badge={<Badge tone="success">在线</Badge>}
              />
              <InsetRow
                icon={<Database className="h-4 w-4" />}
                label="数据库"
                badge={<Badge tone="success">在线</Badge>}
              />
              <InsetRow
                icon={<Wifi className="h-4 w-4" />}
                label="115 OpenAPI"
                badge={
                  <Badge tone={statusQuery.data.openapiReady ? "success" : "warning"}>
                    {statusQuery.data.openapiReady ? "已连接" : "检查配置"}
                  </Badge>
                }
              />
              <InsetRow
                icon={<Activity className="h-4 w-4" />}
                label="爬虫"
                badge={
                  <Badge tone={statusQuery.data.crawlRunning ? "info" : "default"}>
                    {statusQuery.data.crawlRunning ? "运行中" : "空闲"}
                  </Badge>
                }
              />
              <InsetRow
                icon={<Cpu className="h-4 w-4" />}
                label="调试模式"
                badge={
                  <Badge tone={statusQuery.data.debugMode ? "warning" : "default"}>
                    {statusQuery.data.debugMode ? "开启" : "关闭"}
                  </Badge>
                }
              />
            </div>
          ) : null}
        </Card>

        {/* 2×2 stat cards */}
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            label="资源总数"
            value={formatNumber(statsQuery.data.total)}
            icon={<Activity className="h-8 w-8" />}
            tone="primary"
          />
          <StatCard
            label="已下载"
            value={formatNumber(statsQuery.data.downloaded)}
            icon={<CheckCircle2 className="h-8 w-8" />}
            tone="success"
          />
          <StatCard
            label="待处理"
            value={formatNumber(statsQuery.data.pending)}
            icon={<Clock3 className="h-8 w-8" />}
            tone="warning"
          />
          <StatCard
            label="失败重试"
            value={formatNumber(statsQuery.data.retryPending)}
            icon={<RotateCcw className="h-8 w-8" />}
            tone="danger"
          />
        </div>
      </div>

      {/* ── Charts row ── */}
      <div className="mb-4 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">近 30 天抓取量</h2>
            <Badge tone="info">帖子/天</Badge>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendQuery.data.items}>
                <Tooltip
                  contentStyle={{
                    background: "rgba(255,255,255,0.8)",
                    border: "1px solid rgba(255,255,255,0.7)",
                    borderRadius: 8,
                    backdropFilter: "blur(20px)",
                  }}
                />
                <Line type="monotone" dataKey="total" name="总数" stroke="#007AFF" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="downloaded" name="已下载" stroke="#34C759" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">板块占比</h2>
            <Badge>全部时间</Badge>
          </div>
          <div className="flex h-56 items-center justify-center gap-6">
            <ResponsiveContainer width={140} height={140}>
              <PieChart>
                <Pie
                  data={statsQuery.data.bySection}
                  dataKey="total"
                  nameKey="sectionName"
                  innerRadius={38}
                  outerRadius={60}
                  paddingAngle={2}
                >
                  {statsQuery.data.bySection.map((section, index) => (
                    <Cell key={section.sectionName} fill={CHART_PALETTE[index % CHART_PALETTE.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-col gap-1.5 text-xs">
              {statsQuery.data.bySection.slice(0, 5).map((section, index) => (
                <div key={section.sectionName} className="flex min-w-0 items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ background: CHART_PALETTE[index % CHART_PALETTE.length] }}
                  />
                  <span className="min-w-0 truncate text-foreground">{section.sectionName}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* ── Recent crawls table ── */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">最近抓取</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">标题</th>
                <th className="pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">板块</th>
                <th className="pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">状态</th>
                <th className="pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">时间</th>
              </tr>
            </thead>
            <tbody>
              {statsQuery.data.recent.map((item) => (
                <tr key={item.id} className="border-t border-border/60">
                  <td className="max-w-sm py-3 pr-4 font-medium"><div className="text-cell">{item.title}</div></td>
                  <td className="py-3 pr-4"><div className="max-w-32 truncate">{item.sectionName}</div></td>
                  <td className="py-3 pr-4">
                    <Badge tone={item.isDownload ? "success" : "warning"}>
                      {item.isDownload ? "已下载" : "待处理"}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 font-mono text-xs text-muted-foreground">
                    {formatDateTime(item.createdAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

function InsetRow({
  icon,
  label,
  badge,
}: {
  icon: React.ReactNode;
  label: string;
  badge: React.ReactNode;
}) {
  return (
    <div className="inset-row">
      <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      {badge}
    </div>
  );
}
