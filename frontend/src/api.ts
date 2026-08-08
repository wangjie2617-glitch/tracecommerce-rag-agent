import axios, { AxiosError } from "axios";
import type {
  ApiEnvelope,
  ChatAnswer,
  ConversationSummary,
  DocumentList,
  IngestionJob,
  KnowledgeSource,
  LoginResult,
  ReadyStatus,
  RequestTrace,
  User
} from "./types";

const TOKEN_KEY = "tracecommerce_access_token";
const USER_KEY = "tracecommerce_user";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60_000,
  headers: { "Content-Type": "application/json" }
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearSession();
      window.dispatchEvent(new CustomEvent("tracecommerce:unauthorized"));
    }
    return Promise.reject(error);
  }
);

export function getErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : "请求失败，请稍后重试";
  }
  const payload = error.response?.data as
    | { message?: string; detail?: string | Array<{ msg?: string }> }
    | undefined;
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join("；");
  }
  return payload?.message || error.message || "接口请求失败";
}

export function saveSession(result: LoginResult): void {
  sessionStorage.setItem(TOKEN_KEY, result.access_token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(result.user));
}

export function clearSession(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function loadSession(): { token: string; user: User } | null {
  const token = sessionStorage.getItem(TOKEN_KEY);
  const rawUser = sessionStorage.getItem(USER_KEY);
  if (!token || !rawUser) return null;
  try {
    return { token, user: JSON.parse(rawUser) as User };
  } catch {
    clearSession();
    return null;
  }
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const response = await api.post<ApiEnvelope<LoginResult>>("/auth/login", {
    email,
    password
  });
  return response.data.data;
}

export async function getMe(): Promise<User> {
  const response = await api.get<ApiEnvelope<User>>("/auth/me");
  return response.data.data;
}

export async function queryAgent(
  query: string,
  threadId?: string
): Promise<ChatAnswer> {
  const response = await api.post<ApiEnvelope<ChatAnswer>>("/chat/query", {
    query,
    thread_id: threadId || null,
    filters: {}
  });
  return response.data.data;
}

export async function listConversations(): Promise<ConversationSummary[]> {
  const response =
    await api.get<ApiEnvelope<ConversationSummary[]>>("/chat/conversations");
  return response.data.data;
}

export async function submitFeedback(
  requestId: string,
  helpful: boolean
): Promise<void> {
  await api.post("/chat/feedback", {
    request_id: requestId,
    helpful,
    comment: null
  });
}

export async function listKnowledgeSources(): Promise<KnowledgeSource[]> {
  const response =
    await api.get<ApiEnvelope<KnowledgeSource[]>>("/knowledge-sources");
  return response.data.data;
}

export async function syncKnowledgeSource(
  sourceId: string
): Promise<IngestionJob> {
  const response = await api.post<ApiEnvelope<IngestionJob>>(
    `/knowledge-sources/${sourceId}/sync`
  );
  return response.data.data;
}

export async function listDocuments(sourceId?: string): Promise<DocumentList> {
  const response = await api.get<ApiEnvelope<DocumentList>>("/documents", {
    params: sourceId ? { source_id: sourceId } : undefined
  });
  return response.data.data;
}

export async function uploadDocument(input: {
  sourceId: string;
  file: File;
  businessCategory?: string;
}): Promise<IngestionJob> {
  const body = new FormData();
  body.append("source_id", input.sourceId);
  body.append("file", input.file);
  body.append("language", "zh-CN");
  if (input.businessCategory) {
    body.append("business_category", input.businessCategory);
  }
  const response = await api.post<ApiEnvelope<IngestionJob>>(
    "/documents/upload",
    body,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data.data;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/documents/${documentId}`);
}

export async function getTrace(requestId: string): Promise<RequestTrace> {
  const response = await api.get<ApiEnvelope<RequestTrace>>(
    `/traces/${requestId}`
  );
  return response.data.data;
}

export async function getReadyStatus(): Promise<ReadyStatus> {
  const response = await axios.get<ApiEnvelope<ReadyStatus>>("/ready", {
    timeout: 5_000
  });
  return response.data.data;
}
