import { apiClient } from "./client";

export interface PdfPreview {
  target_table: string;
  columns: string[];
  records: Record<string, unknown>[];
  warnings: string[];
}

export interface PdfConfirmResult {
  inserted_count: number;
  skipped_count: number;
  warnings: string[];
}

export function uploadPdf(file: File, dbConnectionId: number, targetTable: string) {
  const form = new FormData();
  form.append("file", file);
  form.append("db_connection_id", String(dbConnectionId));
  form.append("target_table", targetTable);
  return apiClient
    .post<PdfPreview>("/api/pdf/upload", form, { headers: { "Content-Type": "multipart/form-data" } })
    .then((res) => res.data);
}

export function confirmPdfInsert(dbConnectionId: number, targetTable: string, records: Record<string, unknown>[]) {
  return apiClient
    .post<PdfConfirmResult>("/api/pdf/confirm", {
      db_connection_id: dbConnectionId,
      target_table: targetTable,
      records,
    })
    .then((res) => res.data);
}
