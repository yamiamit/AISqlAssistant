// Shared TypeScript types, mirroring the backend's Pydantic response schemas
// (see backend/app/schemas/*.py) so the frontend and API never drift silently.

export interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
}

export interface DBConnection {
  id: number;
  name: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  ssl_mode: string;
  is_demo: boolean;
  // null = never probed (a connection saved before scoped access existed).
  // Deliberately not defaulted to false: "unknown" and "read-only" are
  // different claims and the UI shouldn't make the safer-sounding one for free.
  has_write_access: boolean | null;
  schema_updated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SchemaColumn {
  name: string;
  type: string;
  nullable: boolean;
  is_primary_key: boolean;
}

export interface SchemaForeignKey {
  column: string | null;
  references_table: string;
  references_column: string | null;
}

export interface SchemaTable {
  name: string;
  columns: SchemaColumn[];
  primary_keys: string[];
  foreign_keys: SchemaForeignKey[];
}

export interface SchemaResponse {
  tables: SchemaTable[];
}

export interface AccessScript {
  role: string;
  password: string;
  tables: string[];
  script: string;
  connection_string: string;
}

export type ChartType = "bar" | "line" | "pie" | null;

export interface Message {
  id: number;
  conversation_id: number;
  prompt_text: string;
  generated_sql: string | null;
  explanation: string | null;
  result_columns: string[] | null;
  result_rows: Record<string, unknown>[] | null;
  row_count: number | null;
  execution_time_ms: number | null;
  chart_type: ChartType;
  error_message: string | null;
  created_at: string;
}

export interface ConversationSummary {
  id: number;
  title: string;
  db_connection_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: Message[];
}

export interface SavedQuery {
  id: number;
  name: string;
  prompt_text: string;
  sql_text: string;
  db_connection_id: number | null;
  created_at: string;
}
