// Server types
export interface ServerConfig {
  id: number;
  service_type: 'plex' | 'jellyfin' | 'seerr';
  name: string;
  url: string;
  api_key?: string;
  token?: string;
  is_active: boolean;
  last_test_at?: string;
  last_test_status?: 'success' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface ServerConfigCreate {
  service_type: 'plex' | 'jellyfin' | 'seerr';
  name: string;
  url: string;
  api_key?: string;
  token?: string;
  is_active?: boolean;
}

export interface ServerConfigUpdate {
  name?: string;
  url?: string;
  api_key?: string;
  token?: string;
  is_active?: boolean;
}

// User types
export interface UserMapping {
  id: number;
  plex_username: string;
  plex_user_id?: string;
  jellyfin_user_id: string;
  seerr_user_id: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface UserMappingCreate {
  plex_username: string;
  plex_user_id?: string;
  jellyfin_user_id: string;
  seerr_user_id: string;
  is_active?: boolean;
  notes?: string;
}

export interface ExternalUser {
  id: number;
  service_type: 'plex' | 'jellyfin' | 'seerr';
  external_id: string;
  username: string;
  email?: string;
  last_synced_at: string;
}

export interface UserMappingStats {
  mapping_id: number;
  plex_username: string;
  jellyfin_user_id: string;
  seerr_user_id: string;
  watchlist_total: number;
  watchlist_synced: number;
  watchlist_pending: number;
  watchlist_failed: number;
  seerr_requests_total: number;
  seerr_requests_synced: number;
  seerr_requests_pending: number;
  seerr_requests_failed: number;
}

// Settings types
export interface AppSettings {
  sync_plex_watchlist: boolean;
  sync_seerr_requests: boolean;
  polling_interval: number;
  webhook_enabled: boolean;
  log_level: string;
  [key: string]: any;
}

// Dashboard types
export interface DashboardStats {
  servers_connected: number;
  servers_total: number;
  users_mapped: number;
  users_total: number;
  items_synced: number;
  items_pending: number;
  items_failed: number;
  last_sync?: string | null;
  seerr_request: SyncStats;
  unmapped: SyncStats;
  watchlist_to_seerr: SyncStats;
  favorites: SyncStats;
}

export interface SyncStats {
  total: number;
  synced: number;
  pending: number;
  failed: number;
}

export interface ActivityItem {
  id: number;
  title: string;
  media_type: string;
  status: 'synced' | 'pending' | 'failed';
  source: string;
  user: string;
  timestamp: string;
  error?: string;
}

export interface ActivityResponse {
  items: ActivityItem[];
  page: number;
  per_page: number;
  total: number;
  pages: number;
}

// System types
export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  database: string;
  servers: Record<string, {
    configured: boolean;
    connected: boolean;
    last_test?: string;
  }>;
}

export interface SystemInfo {
  version: string;
  python_version: string;
  platform: string;
  database_type: string;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
}