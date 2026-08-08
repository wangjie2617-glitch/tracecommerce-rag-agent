export interface ApiEnvelope<T> {
  success: boolean;
  request_id: string;
  data: T;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  roles: string[];
  is_active: boolean;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Citation {
  document_id: string;
  chunk_id: string;
  title: string;
  section_title: string | null;
  source_url: string;
  quoted_text: string;
  retrieval_score: number;
  rerank_score: number | null;
  crawled_at: string;
}

export interface TraceStep {
  node: string;
  status: string;
  duration_ms: number;
  started_at: string;
  ended_at: string;
  input_summary?: string | null;
  output_summary?: string | null;
  error?: string | null;
}

export interface ChatAnswer {
  request_id: string;
  thread_id: string;
  answer: string;
  evidence_score?: number;
  evidence_level?: "insufficient" | "low" | "medium" | "high";
  /** @deprecated Compatibility field from older API responses. */
  confidence: number;
  grounded: boolean;
  intent: string;
  language: string;
  citations: Citation[];
  trace: TraceStep[];
  warnings: string[];
}

export interface ConversationSummary {
  thread_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSource {
  id: string;
  name: string;
  company_name: string;
  source_type: string;
  base_url: string | null;
  config: Record<string, unknown>;
  is_active: boolean;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  source_id: string;
  title: string;
  source_url: string;
  source_type: string;
  language: string;
  country_or_region: string | null;
  business_category: string | null;
  content_hash: string;
  current_version: number;
  is_active: boolean;
  crawled_at: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentList {
  items: KnowledgeDocument[];
  count: number;
}

export interface IngestionJob {
  id: string;
  source_id: string | null;
  status: string;
  pages_discovered: number;
  documents_created: number;
  documents_updated: number;
  documents_unchanged: number;
  chunks_written: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface RequestTrace {
  result: ChatAnswer;
  retrieved: Array<Record<string, unknown>>;
}

export interface ReadyStatus {
  status: string;
  database: string;
  vector_store: string;
}

export type ChatMessage =
  | {
      id: string;
      role: "user";
      content: string;
    }
  | {
      id: string;
      role: "assistant";
      content: string;
      result: ChatAnswer;
    };
