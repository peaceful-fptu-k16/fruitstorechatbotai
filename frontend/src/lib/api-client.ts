export interface Product {
  id: number;
  name: string;
  category: string;
  price: number;
  stock: number;
  sweetness_level: number;
  sourness_level: number;
  seed_level: number;
  juiciness_level: number;
  aroma_level: number;
  crunchiness_level: number;
  fiber_level: number;
  vitamin_c_level: number;
  sugar_content_level: number;
  calories_per_100g: number;
  shelf_life_days: number;
  texture: string;
  color: string;
  best_use: string;
  origin: string;
  season: string;
  description: string;
}

export interface Citation {
  source_id: string;
  source_type: string;
  snippet: string;
  score: number;
}

export interface ChatResponse {
  trace_id: string;
  intent: string;
  confidence: number;
  answer: string;
  products: Product[];
  citations: Citation[];
  fallback: boolean;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function sendChatMessage(payload: {
  user_id: string;
  session_id: string;
  message: string;
  language?: string;
}): Promise<ChatResponse> {
  return requestJson<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ ...payload, language: payload.language ?? "vi" }),
  });
}

export async function fetchProducts(params?: {
  query?: string;
  available_only?: boolean;
  limit?: number;
}): Promise<{ total: number; items: Product[] }> {
  const search = new URLSearchParams();
  if (params?.query) {
    search.set("query", params.query);
  }
  if (params?.available_only) {
    search.set("available_only", "true");
  }
  if (params?.limit) {
    search.set("limit", String(params.limit));
  }

  const queryString = search.toString();
  const suffix = queryString ? `?${queryString}` : "";
  return requestJson<{ total: number; items: Product[] }>(`/products${suffix}`);
}
