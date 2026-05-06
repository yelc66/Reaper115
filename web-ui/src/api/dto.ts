export type DashboardStatsDto = {
  total: number;
  downloaded: number;
  pending: number;
  retry_pending: number;
  by_section: SectionStatDto[];
  recent: SehuaItemDto[];
};

export type SectionStatDto = {
  section_name: string;
  total: number;
  downloaded: number;
};

export type TrendResponseDto = {
  days: number;
  items: Array<{ date: string; total: number; downloaded: number }>;
};

export type SehuaItemDto = {
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

export type SehuaListResponseDto = {
  page: number;
  size: number;
  total: number;
  items: SehuaItemDto[];
};

export type OfflineTaskDto = {
  id: number;
  title: string;
  save_path?: string | null;
  magnet?: string | null;
  is_download: number;
  retry_count: number;
  completed_at?: string | null;
  created_at?: string | null;
};

export type CrawlStatusDto = {
  running: boolean;
};

export type SystemStatusDto = {
  openapi_ready: boolean;
  crawl_running: boolean;
  debug_mode: boolean;
  paths: Record<string, string>;
  user_info?: unknown;
};
