import { api } from "./client";
import type {
  CrawlStatus,
  DashboardStats,
  OfflineTask,
  SehuaListResponse,
  StrategyRule,
  StrategyRuleInput,
  SystemStatus,
  TrendResponse,
} from "./types";

export const dashboardApi = {
  stats: async () => (await api.get<DashboardStats>("/api/dashboard/stats")).data,
  trend: async (days = 30) => (await api.get<TrendResponse>("/api/dashboard/trend", { params: { days } })).data,
};

export const sehuaApi = {
  list: async (params: { page: number; size: number; section?: string; status?: string; keyword?: string }) =>
    (
      await api.get<SehuaListResponse>("/api/sehua", {
        params: {
          ...params,
          status: params.status === "" ? undefined : params.status,
          section: params.section || undefined,
          keyword: params.keyword || undefined,
        },
      })
    ).data,
  download: async (id: number) => (await api.post(`/api/sehua/${id}/download`)).data,
  batchDownload: async (ids: number[]) => (await api.post("/api/sehua/batch-download", { ids })).data,
  delete: async (id: number) => (await api.delete(`/api/sehua/${id}`)).data,
};

export const strategyApi = {
  list: async () => (await api.get<{ items: StrategyRule[] }>("/api/strategy/rules")).data,
  create: async (rule: StrategyRuleInput) => (await api.post("/api/strategy/rules", rule)).data,
  update: async (id: number, rule: StrategyRuleInput) => (await api.put(`/api/strategy/rules/${id}`, rule)).data,
  delete: async (id: number) => (await api.delete(`/api/strategy/rules/${id}`)).data,
  test: async (payload: { pattern: string; title: string }) =>
    (await api.post<{ matched: boolean }>("/api/strategy/test", payload)).data,
};

export const tasksApi = {
  list: async () => (await api.get<{ items: OfflineTask[] }>("/api/tasks")).data,
  retry: async (id: number) => (await api.post(`/api/tasks/${id}/retry`)).data,
  delete: async (id: number) => (await api.delete(`/api/tasks/${id}`)).data,
  clear: async () => (await api.delete("/api/tasks/all")).data,
};

export const crawlApi = {
  trigger: async (date?: string) => (await api.post("/api/crawl/trigger", { date: date || null })).data,
  status: async () => (await api.get<CrawlStatus>("/api/crawl/status")).data,
};

export const systemApi = {
  status: async () => (await api.get<SystemStatus>("/api/system/status")).data,
  config: async () => (await api.get<{ config: Record<string, unknown> }>("/api/system/config")).data,
  updateConfig: async (config: Record<string, unknown>) => (await api.put("/api/system/config", { config })).data,
};
