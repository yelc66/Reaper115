import { useQuery } from "@tanstack/react-query";
import { BarChart3, CheckCircle2, Clock3, FolderOpen, RotateCcw, ServerCog } from "lucide-react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { dashboardApi, systemApi } from "../api/queries";
import { Badge, Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { errorMessage, formatDateTime, formatNumber } from "../lib/utils";

const CHART_PALETTE = ["#007AFF", "#5ACBFA", "#B0D9FF", "#34C759", "#5856D6", "#FF9500", "#8E8E93"];

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

  const cards = [
    { label: "资源总数", value: statsQuery.data.total, icon: BarChart3, tone: "text-primary" },
    { label: "已离线", value: statsQuery.data.downloaded, icon: CheckCircle2, tone: "text-emerald-400" },
    { label: "待处理", value: statsQuery.data.pending, icon: Clock3, tone: "text-amber-400" },
    { label: "重试队列", value: statsQuery.data.retryPending, icon: RotateCcw, tone: "text-rose-400" },
  ];

  return (
    <>
      <section className="mb-5 rounded-lg border border-white/70 bg-white/54 p-5 shadow-glass backdrop-blur-2xl dark:border-white/10 dark:bg-white/10">
        <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-lg font-semibold">
              <ServerCog className="h-5 w-5 text-primary" />
              系统状态
            </div>
            <p className="mt-1 text-sm text-muted-foreground">OpenAPI、Token、爬虫和运行路径状态，每 10 秒自动刷新</p>
          </div>
          {statusQuery.data ? (
            <Badge tone={statusQuery.data.openapiReady && statusQuery.data.tokenFileExists ? "success" : "warning"}>
              {statusQuery.data.openapiReady && statusQuery.data.tokenFileExists ? "基础服务正常" : "需要检查配置"}
            </Badge>
          ) : null}
        </div>

        {statusQuery.isPending ? <LoadingState /> : null}
        {statusQuery.isError ? <ErrorState message={errorMessage(statusQuery.error)} /> : null}
        {statusQuery.data ? (
          <div className="grid gap-4 lg:grid-cols-[0.78fr_1.22fr]">
            <div className="rounded-lg border border-white/70 bg-white/58 p-4 shadow-panel backdrop-blur-xl dark:border-white/10 dark:bg-white/10">
              <h2 className="mb-4 text-sm font-semibold">运行状态</h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                <StatusLine label="115 OpenAPI" active={statusQuery.data.openapiReady} />
                <StatusLine label="Token 文件" active={statusQuery.data.tokenFileExists} />
                <StatusLine
                  label="爬虫状态"
                  active={statusQuery.data.crawlRunning}
                  activeText="运行中"
                  inactiveText="空闲"
                />
                <StatusLine
                  label="调试模式"
                  active={statusQuery.data.debugMode}
                  activeText="开启"
                  inactiveText="关闭"
                />
              </div>
            </div>

            <div className="rounded-lg border border-white/70 bg-white/58 p-4 shadow-panel backdrop-blur-xl dark:border-white/10 dark:bg-white/10">
              <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                <FolderOpen className="h-4 w-4 text-primary" />
                路径
              </h2>
              <div className="grid gap-3 text-xs md:grid-cols-2">
                {Object.entries(statusQuery.data.paths ?? {}).map(([key, value]) => (
                  <div key={key} className="min-w-0 rounded-md bg-white/46 p-3 dark:bg-white/5">
                    <div className="mb-1 text-muted-foreground">{key}</div>
                    <div className="break-all font-mono leading-5">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </section>

      <PageHeader title="Dashboard" description="资源入库、离线状态和最近抓取活动概览" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((item) => (
          <Card key={item.label}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">{item.label}</div>
                <div className="mt-2 text-3xl font-semibold">{formatNumber(item.value)}</div>
              </div>
              <item.icon className={`h-8 w-8 ${item.tone}`} />
            </div>
          </Card>
        ))}
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <h2 className="mb-4 text-base font-semibold">30 日趋势</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendQuery.data.items}>
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8F8F8F" }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#8F8F8F" }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Line type="monotone" dataKey="total" name="总数" stroke="#007AFF" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="downloaded" name="已离线" stroke="#34C759" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h2 className="mb-4 text-base font-semibold">版块分布</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statsQuery.data.bySection}
                  dataKey="total"
                  nameKey="sectionName"
                  innerRadius={60}
                  outerRadius={105}
                  paddingAngle={2}
                >
                  {statsQuery.data.bySection.map((section, index) => (
                    <Cell key={section.sectionName} fill={CHART_PALETTE[index % CHART_PALETTE.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      <Card className="mt-4">
        <h2 className="mb-4 text-base font-semibold">最近入库</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-border text-left text-muted-foreground">
              <tr>
                <th className="py-2 pr-4 font-medium">标题</th>
                <th className="py-2 pr-4 font-medium">版块</th>
                <th className="py-2 pr-4 font-medium">状态</th>
                <th className="py-2 pr-4 font-medium">时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {statsQuery.data.recent.map((item) => (
                <tr key={item.id}>
                  <td className="max-w-xl py-3 pr-4">{item.title}</td>
                  <td className="py-3 pr-4">{item.sectionName}</td>
                  <td className="py-3 pr-4">
                    <Badge tone={item.isDownload ? "success" : "warning"}>
                      {item.isDownload ? "已离线" : "待处理"}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{formatDateTime(item.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
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
    <div className="flex items-center justify-between gap-3 rounded-md bg-white/46 px-3 py-2 dark:bg-white/5">
      <span className="text-sm text-muted-foreground">{label}</span>
      <Badge tone={active ? "success" : "warning"}>{active ? activeText : inactiveText}</Badge>
    </div>
  );
}
