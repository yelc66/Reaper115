export type DashboardStats = {
  total: number;
  downloaded: number;
  pending: number;
  retry_pending: number;
  by_section: SectionStat[];
  recent: SehuaItem[];
};

export type SectionStat = {
  section_name: string;
  total: number;
  downloaded: number;
};

export type TrendResponse = {
  days: number;
  items: Array<{ date: string; total: number; downloaded: number }>;
};

export type SehuaItem = {
  id: number;
  section_name: string;
  av_number?: string | null;
  title: string;
  movie_type?: string | null;
  size?: string | null;
  magnet?: string | null;
  post_url?: string | null;
  publish_date?: string | null;
  pub_url?: string | null;
  image_path?: string | null;
  save_path?: string | null;
  is_download: number;
  created_at?: string | null;
};

export type SehuaListResponse = {
  page: number;
  size: number;
  total: number;
  items: SehuaItem[];
};

export type StrategyRule = {
  id: number;
  section_name: string;
  strategy_name: string;
  pattern: string;
  specify_save_path?: string | null;
};

export type StrategyRuleInput = Omit<StrategyRule, "id">;

export type OfflineTask = {
  id: number;
  title: string;
  save_path?: string | null;
  magnet?: string | null;
  is_download: number;
  retry_count: number;
  completed_at?: string | null;
  created_at?: string | null;
};

export type CrawlStatus = {
  running: boolean;
};

export type SystemStatus = {
  openapi_ready: boolean;
  token_file_exists: boolean;
  crawl_running: boolean;
  debug_mode: boolean;
  paths: Record<string, string>;
  user_info?: unknown;
};
