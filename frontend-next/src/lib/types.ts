export interface ChatRequest {
  user_query: string;
  session_id?: string;
  history?: ChatMessage[];
}

export interface ChatResponse {
  query_id: string;
  status: 'sql_generated' | 'invalid_params' | 'no_template' | 'error';
  user_query: string;
  sql_query?: string;
  tool_name?: string;
  template_key?: string;
  params?: Record<string, unknown>;
  reasoning?: string;
  error?: string;
  timestamp: string;
}

export interface ExecuteRequest {
  sql_query: string;
  params?: Record<string, unknown>;
  user_query?: string;
  session_id?: string;
}

export interface ExecuteResponse {
  query_id: string;
  status: 'success' | 'error';
  sql_query: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  error?: string;
  timestamp: string;
}

export interface ChartConfig {
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'area' | 'table';
  x_col: string;
  y_cols: string[];
  title: string;
}

export interface AnalyzeRequest {
  user_query: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  session_id?: string;
}

export interface AnalyzeResponse {
  summary: string;
  chart: ChartConfig;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface QueryResult {
  chat: ChatResponse;
  execute?: ExecuteResponse;
  analyze?: AnalyzeResponse;
}

export interface ConversationEntry {
  id: string;
  userQuery: string;
  result: QueryResult;
  timestamp: string;
}
