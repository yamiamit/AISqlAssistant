import { apiClient } from "./client";
import type { DBConnection, SchemaResponse } from "../types";

export interface DBConnectionInput {
  name: string;
  connection_string?: string;
  host?: string;
  port?: number;
  database_name?: string;
  username?: string;
  password?: string;
  ssl_mode?: string;
}

export function listConnections() {
  return apiClient.get<DBConnection[]>("/api/connections").then((res) => res.data);
}

export function testConnection(payload: DBConnectionInput) {
  return apiClient
    .post<{ success: boolean; message: string }>("/api/connections/test", payload)
    .then((res) => res.data);
}

export function createConnection(payload: DBConnectionInput) {
  return apiClient.post<DBConnection>("/api/connections", payload).then((res) => res.data);
}

export function updateConnection(id: number, payload: Partial<DBConnectionInput>) {
  return apiClient.put<DBConnection>(`/api/connections/${id}`, payload).then((res) => res.data);
}

export function deleteConnection(id: number) {
  return apiClient.delete(`/api/connections/${id}`);
}

export function getSchema(id: number) {
  return apiClient.get<SchemaResponse>(`/api/connections/${id}/schema`).then((res) => res.data);
}

export function refreshSchema(id: number) {
  return apiClient.post<SchemaResponse>(`/api/connections/${id}/refresh-schema`).then((res) => res.data);
}
