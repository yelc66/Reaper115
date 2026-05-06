import type {
  DashboardStatsDto,
  OfflineTaskDto,
  SehuaItemDto,
  SehuaListResponseDto,
  SystemStatusDto,
} from "./dto";
import type {
  DashboardStats,
  OfflineTask,
  SehuaItem,
  SehuaListResponse,
  SystemStatus,
} from "./models";

export function mapSehuaItem(item: SehuaItemDto): SehuaItem {
  return {
    id: item.id,
    sectionName: item.section_name,
    avNumber: item.av_number,
    title: item.title,
    movieType: item.movie_type,
    size: item.size,
    magnet: item.magnet,
    postUrl: item.post_url,
    publishDate: item.publish_date,
    pubUrl: item.pub_url,
    imagePath: item.image_path,
    savePath: item.save_path,
    isDownload: item.is_download,
    createdAt: item.created_at,
  };
}

export function mapDashboardStats(stats: DashboardStatsDto): DashboardStats {
  return {
    total: stats.total,
    downloaded: stats.downloaded,
    pending: stats.pending,
    retryPending: stats.retry_pending,
    bySection: stats.by_section.map((section) => ({
      sectionName: section.section_name,
      total: section.total,
      downloaded: section.downloaded,
    })),
    recent: stats.recent.map(mapSehuaItem),
  };
}

export function mapSehuaListResponse(response: SehuaListResponseDto): SehuaListResponse {
  return {
    page: response.page,
    size: response.size,
    total: response.total,
    items: response.items.map(mapSehuaItem),
  };
}

export function mapOfflineTask(task: OfflineTaskDto): OfflineTask {
  return {
    id: task.id,
    title: task.title,
    savePath: task.save_path,
    magnet: task.magnet,
    isDownload: task.is_download,
    retryCount: task.retry_count,
    completedAt: task.completed_at,
    createdAt: task.created_at,
  };
}

export function mapSystemStatus(status: SystemStatusDto): SystemStatus {
  return {
    openapiReady: status.openapi_ready,
    crawlRunning: status.crawl_running,
    debugMode: status.debug_mode,
    paths: status.paths,
    userInfo: status.user_info,
  };
}
