import { useQuery } from "@tanstack/react-query";
import { BarChart3, CheckCircle2, Clock3, RotateCcw } from "lucide-react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { dashboardApi } from "../api/queries";
import { Badge, Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { errorMessage, formatDateTime, formatNumber } from "../lib/utils";

const CHART_PALETTE = ["#5E6AD2", "#4DAA81", "#E8C547", "#E06C75", "#9B86E8", "#38BDF8", "#6B7280"];

export function Dashboard() {
  const statsQuery = useQuery({ queryKey: ["dashboard", "stats"], queryFn: dashboardApi.stats });
  const trendQuery = useQuery({ queryKey: ["dashboard", "trend", 30], queryFn: () => dashboardApi.trend(30) });

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
                <Line type="monotone" dataKey="total" name="总数" stroke="#5E6AD2" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="downloaded" name="已离线" stroke="#4DAA81" strokeWidth={2} dot={false} />
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
