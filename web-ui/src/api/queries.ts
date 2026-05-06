import { api } from "./client";
import type {
  CrawlStatusDto,
  DashboardStatsDto,
  OfflineTaskDto,
  SehuaListResponseDto,
  StrategyRuleDto,
  SystemStatusDto,
  TrendResponseDto,
} from "./dto";
import {
  mapDashboardStats,
  mapOfflineTask,
  mapSehuaListResponse,
  mapStrategyRule,
  mapSystemStatus,
  toStrategyRuleInputDto,
} from "./mappers";
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

type SehuaListParams = {
  page: number;
  size: number;
  section?: string;
  status?: string;
  keyword?: string;
};

type StrategyTestPayload = {
  pattern: string;
  title: string;
};

type CrawlTriggerPayload = {
  mode?: "today" | "yesterday" | "7days";
};

export const authApi = {
  status: async () => (await api.get<{ auth_required: boolean }>("/api/auth/status")).data,
  login: async (key: string) => (await api.post<{ ok: boolean; auth_required: boolean }>("/api/auth/login", { key })).data,
};

export const dashboardApi = {
  stats: async () => mapDashboardStats((await api.get<DashboardStatsDto>("/api/dashboard/stats")).data),
  trend: async (days = 30): Promise<TrendResponse> =>
    (await api.get<TrendResponseDto>("/api/dashboard/trend", { params: { days } })).data,
};

export const sehuaApi = {
  list: async (params: SehuaListParams) =>
    mapSehuaListResponse(
      (
        await api.get<SehuaListResponseDto>("/api/sehua", {
          params: {
            ...params,
            status: params.status === "" ? undefined : params.status,
            section: params.section || undefined,
            keyword: params.keyword || undefined,
          },
        })
      ).data,
    ),
  download: async (id: number) => (await api.post(`/api/sehua/${id}/download`)).data,
  batchDownload: async (ids: number[]) => (await api.post("/api/sehua/batch-download", { ids })).data,
  delete: async (id: number) => (await api.delete(`/api/sehua/${id}`)).data,
  batchDelete: async (ids: number[]) => (await api.delete("/api/sehua/batch-delete", { data: { ids } })).data,
};

export const strategyApi = {
  list: async () => {
    const response = (await api.get<{ items: StrategyRuleDto[] }>("/api/strategy/rules")).data;
    return { items: response.items.map(mapStrategyRule) };
  },
  create: async (rule: StrategyRuleInput) => (await api.post("/api/strategy/rules", toStrategyRuleInputDto(rule))).data,
  update: async (id: number, rule: StrategyRuleInput) =>
    (await api.put(`/api/strategy/rules/${id}`, toStrategyRuleInputDto(rule))).data,
  delete: async (id: number) => (await api.delete(`/api/strategy/rules/${id}`)).data,
  toggleActive: async (id: number, active: boolean) =>
    (await api.patch(`/api/strategy/rules/${id}/active`, { active })).data,
  test: async (payload: StrategyTestPayload) =>
    (await api.post<{ matched: boolean }>("/api/strategy/test", payload)).data,
};

export const tasksApi = {
  list: async () => {
    const response = (await api.get<{ items: OfflineTaskDto[] }>("/api/tasks")).data;
    return { items: response.items.map(mapOfflineTask) };
  },
  retry: async (id: number) => (await api.post(`/api/tasks/${id}/retry`)).data,
  delete: async (id: number) => (await api.delete(`/api/tasks/${id}`)).data,
  clear: async () => (await api.delete("/api/tasks/all")).data,
};

export const crawlApi = {
  trigger: async (payload?: string | CrawlTriggerPayload) => {
    const body =
      typeof payload === "string"
        ? { date: payload || null }
        : {
            mode: payload?.mode || "today",
          };
    return (await api.post("/api/crawl/trigger", body)).data;
  },
  status: async (): Promise<CrawlStatus> => (await api.get<CrawlStatusDto>("/api/crawl/status")).data,
};

export const systemApi = {
  status: async () => mapSystemStatus((await api.get<SystemStatusDto>("/api/system/status")).data),
  config: async () => (await api.get<{ config: Record<string, unknown> }>("/api/system/config")).data,
  updateConfig: async (config: Record<string, unknown>) => (await api.put("/api/system/config", { config })).data,
  testTelegram: async () => (await api.post<{ ok: boolean; message: string }>("/api/system/test/telegram")).data,
  test115: async () => (await api.post<{ ok: boolean; message: string }>("/api/system/test/115")).data,
  get115Qrcode: async () => (await api.get<{ ok: boolean; qr_b64: string }>("/api/system/115/qrcode")).data,
};
