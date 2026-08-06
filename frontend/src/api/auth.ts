import { apiClient } from "./client";
import type { User } from "../types";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export function register(email: string, password: string, full_name: string) {
  return apiClient
    .post<TokenResponse>("/api/auth/register", { email, password, full_name })
    .then((res) => res.data);
}

export function login(email: string, password: string) {
  return apiClient.post<TokenResponse>("/api/auth/login", { email, password }).then((res) => res.data);
}

export function fetchCurrentUser() {
  return apiClient.get<User>("/api/auth/me").then((res) => res.data);
}
