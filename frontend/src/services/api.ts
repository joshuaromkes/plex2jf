import axios, { type AxiosError, type AxiosResponse } from 'axios';
import type { ApiResponse } from '../types';

// Create axios instance
const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ApiResponse<unknown>>) => {
    if (error.response) {
      // Server responded with error
      console.error('API Error:', error.response.data);
      return Promise.reject(error.response.data);
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error:', error.request);
      return Promise.reject({ success: false, error: { message: 'Network error - please check your connection' } });
    } else {
      // Something else happened
      console.error('Error:', error.message);
      return Promise.reject({ success: false, error: { message: error.message } });
    }
  }
);

// Generic API methods
export async function get<T>(url: string): Promise<T> {
  const response = await api.get<ApiResponse<T>>(url);
  if (!response.data.success) {
    throw new Error(response.data.error?.message || 'Unknown error');
  }
  return response.data.data as T;
}

export async function post<T>(url: string, data?: unknown): Promise<T> {
  const response = await api.post<ApiResponse<T>>(url, data);
  if (!response.data.success) {
    throw new Error(response.data.error?.message || 'Unknown error');
  }
  return response.data.data as T;
}

export async function put<T>(url: string, data?: unknown): Promise<T> {
  const response = await api.put<ApiResponse<T>>(url, data);
  if (!response.data.success) {
    throw new Error(response.data.error?.message || 'Unknown error');
  }
  return response.data.data as T;
}

export async function del<T>(url: string): Promise<T> {
  const response = await api.delete<ApiResponse<T>>(url);
  if (!response.data.success) {
    throw new Error(response.data.error?.message || 'Unknown error');
  }
  return response.data.data as T;
}

import type { 
  ServerConfig, 
  ServerConfigCreate, 
  ServerConfigUpdate,
  UserMapping,
  UserMappingCreate,
  ExternalUser,
  AppSettings,
  DashboardStats,
  ActivityResponse,
  HealthStatus,
  SystemInfo
} from '../types';

// Server API
export const serversApi = {
  getAll: () => get<ServerConfig[]>('/api/servers'),
  getById: (id: number) => get<ServerConfig>(`/api/servers/${id}`),
  create: (data: ServerConfigCreate) => post<ServerConfig>('/api/servers', data),
  update: (id: number, data: ServerConfigUpdate) => put<ServerConfig>(`/api/servers/${id}`, data),
  delete: (id: number) => del<{ message: string }>(`/api/servers/${id}`),
  test: (id: number) => post<{ success: boolean; message: string }>(`/api/servers/${id}/test`),
};

// Users API
export const usersApi = {
  getMappings: () => get<UserMapping[]>('/api/users/mappings'),
  createMapping: (data: UserMappingCreate) => post<UserMapping>('/api/users/mappings', data),
  updateMapping: (id: number, data: Partial<UserMappingCreate>) => put<UserMapping>(`/api/users/mappings/${id}`, data),
  deleteMapping: (id: number) => del<{ message: string }>(`/api/users/mappings/${id}`),
  getPlexUsers: () => get<ExternalUser[]>('/api/users/plex'),
  getJellyfinUsers: () => get<ExternalUser[]>('/api/users/jellyfin'),
  getSeerrUsers: () => get<ExternalUser[]>('/api/users/seerr'),
  syncUsers: () => post<{ results: Record<string, string> }>('/api/users/sync'),
};

// Settings API
export const settingsApi = {
  getAll: () => get<AppSettings>('/api/settings'),
  update: (settings: Partial<AppSettings>) => put<AppSettings>('/api/settings', { settings }),
  getByKey: (key: string) => get<unknown>(`/api/settings/${key}`),
  updateByKey: (key: string, value: unknown) => put<AppSettings>(`/api/settings/${key}`, { value }),
};

// Dashboard API
export const dashboardApi = {
  getStats: () => get<DashboardStats>('/api/dashboard/stats'),
  getActivity: (page = 1, perPage = 20, status?: string, source?: string) => {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (status) params.append('status', status);
    if (source) params.append('source', source);
    return get<ActivityResponse>(`/api/dashboard/activity?${params}`);
  },
  triggerSync: () => post<{ message: string }>('/api/dashboard/sync'),
  retryPending: () => post<{ message: string }>('/api/dashboard/retry'),
  retryItem: (id: number) => post<{ message: string }>(`/api/dashboard/retry/${id}`),
};

// System API
export const systemApi = {
  getHealth: () => get<HealthStatus>('/api/system/health'),
  getInfo: () => get<SystemInfo>('/api/system/info'),
  getLogs: (lines = 100) => get<unknown>(`/api/system/logs?lines=${lines}`),
};

export default api;