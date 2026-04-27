import { request } from "../request";

export interface KnowledgeSearchResult {
  file_id: string;
  score: number;
  content: string;
  metadata: Record<string, unknown>;
}

export const knowledgeApi = {
  refresh: () =>
    request<Record<string, unknown>>("/knowledge/refresh", { method: "POST" }),
  listFiles: () => request<Record<string, unknown>[]>("/knowledge/files"),
  listEvents: () => request<Record<string, unknown>[]>("/knowledge/events"),
  health: () => request<{ issues: Record<string, unknown>[] }>("/knowledge/health"),
  search: (payload: {
    query: string;
    categories?: string[];
    tags?: string[];
    limit?: number;
  }) =>
    request<KnowledgeSearchResult[]>("/knowledge/search", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  setSessionCategories: (payload: { session_id: string; categories: string[] }) =>
    request<Record<string, unknown>>("/knowledge/categories", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  writeFile: (payload: { path: string; content: string }) =>
    request<Record<string, unknown>>("/knowledge/write", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  mockUser: () =>
    request<Record<string, unknown>>("/knowledge/mock/user", { method: "POST" }),
  mockTeam: () =>
    request<Record<string, unknown>>("/knowledge/mock/team", { method: "POST" }),
  mockProject: () =>
    request<Record<string, unknown>>("/knowledge/mock/project", { method: "POST" }),
  backup: () => request<Record<string, unknown>>("/knowledge-admin/backup", { method: "POST" }),
  restore: (backup_path: string) =>
    request<Record<string, unknown>>("/knowledge-admin/restore", {
      method: "POST",
      body: JSON.stringify({ backup_path }),
    }),
};
