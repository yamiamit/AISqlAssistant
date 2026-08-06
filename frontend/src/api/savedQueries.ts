import { apiClient } from "./client";
import type { SavedQuery } from "../types";

export interface SavedQueryInput {
  name: string;
  prompt_text: string;
  sql_text: string;
  db_connection_id?: number | null;
}

export function listSavedQueries() {
  return apiClient.get<SavedQuery[]>("/api/saved-queries").then((res) => res.data);
}

export function createSavedQuery(payload: SavedQueryInput) {
  return apiClient.post<SavedQuery>("/api/saved-queries", payload).then((res) => res.data);
}

export function deleteSavedQuery(id: number) {
  return apiClient.delete(`/api/saved-queries/${id}`);
}
