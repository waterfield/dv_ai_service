import {
  ChatRequest, ChatResponse,
  ExecuteRequest, ExecuteResponse,
  AnalyzeRequest, AnalyzeResponse,
} from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(`${BASE}/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(60_000),
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function apiChat(req: ChatRequest): Promise<ChatResponse> {
  return post('/chat', req);
}

export async function apiExecute(req: ExecuteRequest): Promise<ExecuteResponse> {
  return post('/execute', req);
}

export async function apiAnalyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  return post('/analyze', req);
}

export async function apiHealth(): Promise<{ status: string; database_connected: boolean }> {
  const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(5_000) });
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}
