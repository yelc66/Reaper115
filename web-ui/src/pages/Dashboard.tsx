import { useQuery } from "@tanstack/react-query";
import { BarChart3, CheckCircle2, Clock3, RotateCcw } from "lucide-react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { dashboardApi } from "../api/queries";
import { Badge, Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { errorMessage, formatDateTime, formatNumber } from "../lib/utils";

const palette = ["#5E6AD2", "#4DAA81", "#E8C547", "#E06C75", "#9B86E8", "#38BDF8", "#6B7280"];

export function Dashboard() {
  const stats = useQuery({ queryKey: ["dashboard", "stats"], queryFn: dashboardApi.stats });
  const trend = useQuery({ queryKey: ["dashboard", "trend", 30], queryFn: () => dashboardApi.trend(30) });

  if (stats.isPending || trend.isPending) return <LoadingState />;
  if (stats.isError) return <ErrorState message={errorMessage(stats.error)} />;
  if (trend.isError) return <ErrorState message={errorMessage(trend.error)} />;

  const cards = [
    { label: "资源总数", value: stats.data.total, icon: BarChart3, tone: "text-primary" },
    { label: "已离线", value: stats.data.downloaded, icon: CheckCircle2, tone: "text-emerald-400" },
    { label: "待处理", value: stats.data.pending, icon: Clock3, tone: "text-amber-400" },
    { label: "重试队列", value: stats.data.retry_pending, icon: RotateCcw, tone: "text-rose-400" },
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
              <LineChart data={trend.data.items}>
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
                <Pie data={stats.data.by_section} dataKey="total" nameKey="section_name" innerRadius={60} outerRadius={105} paddingAngle={2}>
                  {stats.data.by_section.map((_, index) => (
                    <Cell key={index} fill={palette[index % palette.length]} />
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
              {stats.data.recent.map((item) => (
                <tr key={item.id}>
                  <td className="max-w-xl py-3 pr-4">{item.title}</td>
                  <td className="py-3 pr-4">{item.section_name}</td>
                  <td className="py-3 pr-4">
                    <Badge tone={item.is_download ? "success" : "warning"}>{item.is_download ? "已离线" : "待处理"}</Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{formatDateTime(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
