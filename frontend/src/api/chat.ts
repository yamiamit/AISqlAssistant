import { apiClient } from "./client";
import type { ConversationDetail, ConversationSummary, Message } from "../types";

export interface ChatQueryInput {
  prompt: string;
  db_connection_id: number;
  conversation_id?: number | null;
}

export function runQuery(payload: ChatQueryInput) {
  return apiClient.post<Message>("/api/chat/query", payload).then((res) => res.data);
}

export function listConversations(search?: string) {
  return apiClient
    .get<ConversationSummary[]>("/api/chat/conversations", { params: search ? { search } : undefined })
    .then((res) => res.data);
}

export function getConversation(id: number) {
  return apiClient.get<ConversationDetail>(`/api/chat/conversations/${id}`).then((res) => res.data);
}

export function deleteConversation(id: number) {
  return apiClient.delete(`/api/chat/conversations/${id}`);
}
