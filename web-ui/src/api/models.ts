export type DashboardStats = {
  total: number;
  downloaded: number;
  pending: number;
  retryPending: number;
  bySection: SectionStat[];
  recent: SehuaItem[];
};

export type SectionStat = {
  sectionName: string;
  total: number;
  downloaded: number;
};

export type TrendResponse = {
  days: number;
  items: Array<{ date: string; total: number; downloaded: number }>;
};

export type SehuaItem = {
  id: number;
  sectionName: string;
  avNumber?: string | null;
  title: string;
  movieType?: string | null;
  size?: string | null;
  magnet?: string | null;
  postUrl?: string | null;
  publishDate?: string | null;
  pubUrl?: string | null;
  imagePath?: string | null;
  savePath?: string | null;
  isDownload: number;
  createdAt?: string | null;
};

export type SehuaListResponse = {
  page: number;
  size: number;
  total: number;
  items: SehuaItem[];
};

export type StrategyRule = {
  id: number;
  site: string;
  sectionName: string;
  name: string;
  pattern: string;
  savePath?: string | null;
};

export type StrategyRuleInput = Omit<StrategyRule, "id">;

export type OfflineTask = {
  id: number;
  title: string;
  savePath?: string | null;
  magnet?: string | null;
  isDownload: number;
  retryCount: number;
  completedAt?: string | null;
  createdAt?: string | null;
};

export type CrawlStatus = {
  running: boolean;
};

export type SystemStatus = {
  openapiReady: boolean;
  tokenFileExists: boolean;
  crawlRunning: boolean;
  debugMode: boolean;
  paths: Record<string, string>;
  userInfo?: unknown;
};
