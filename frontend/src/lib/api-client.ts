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

const WINDOWS_1252_REVERSE: Record<number, number> = {
  0x20ac: 0x80,
  0x201a: 0x82,
  0x0192: 0x83,
  0x201e: 0x84,
  0x2026: 0x85,
  0x2020: 0x86,
  0x2021: 0x87,
  0x02c6: 0x88,
  0x2030: 0x89,
  0x0160: 0x8a,
  0x2039: 0x8b,
  0x0152: 0x8c,
  0x017d: 0x8e,
  0x2018: 0x91,
  0x2019: 0x92,
  0x201c: 0x93,
  0x201d: 0x94,
  0x2022: 0x95,
  0x2013: 0x96,
  0x2014: 0x97,
  0x02dc: 0x98,
  0x2122: 0x99,
  0x0161: 0x9a,
  0x203a: 0x9b,
  0x0153: 0x9c,
  0x017e: 0x9e,
  0x0178: 0x9f,
};

const MOJIBAKE_PATTERN = /(?:Ã|Â|Ä|Æ|Å|Ă|áº|á»|đŸ|â€|â‚|â„|â€¦|â€¢)/;
const UTF8_DECODER = new TextDecoder("utf-8", { fatal: true });

/** Convert common Windows-1252/Latin-1 mojibake back to UTF-8 text. */
function repairMojibakeText(text: string): string {
  if (!MOJIBAKE_PATTERN.test(text)) {
    return text;
  }

  const bytes: number[] = [];
  for (const char of text) {
    const codePoint = char.codePointAt(0);
    if (codePoint == null) {
      return text;
    }

    if (codePoint <= 0xff) {
      bytes.push(codePoint);
      continue;
    }

    const mappedByte = WINDOWS_1252_REVERSE[codePoint];
    if (mappedByte == null) {
      return text;
    }
    bytes.push(mappedByte);
  }

  try {
    const repaired = UTF8_DECODER.decode(new Uint8Array(bytes));
    return repaired || text;
  } catch {
    return text;
  }
}

/** Recursively repair API text fields before React renders them. */
function repairResponseStrings<T>(value: T): T {
  if (typeof value === "string") {
    return repairMojibakeText(value) as T;
  }
  if (Array.isArray(value)) {
    return value.map((item) => repairResponseStrings(item)) as T;
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, repairResponseStrings(item)])
    ) as T;
  }
  return value;
}

/** Fetch JSON from the configured backend and surface API errors as Error. */
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
    throw new Error(repairMojibakeText(text) || `Request failed with status ${response.status}`);
  }

  return repairResponseStrings(await response.json()) as T;
}

/** Send one chat turn to the chatbot API. */
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

/** Fetch catalog products for product panels or standalone views. */
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
