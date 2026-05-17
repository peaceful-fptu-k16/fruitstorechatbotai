"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import type { ChatResponse, Product } from "@/lib/api-client";
import { sendChatMessage } from "@/lib/api-client";

import { ProductCard } from "./product-card";
import { QuickReplies } from "./quick-replies";

/* ─── Types ────────────────────────────────────────────── */
type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  intent?: string;
  confidence?: number;
  products?: Product[];
};

/* ─── Quick reply options ─────────────────────────────── */
type QuickOpt = { label: string; value: string };
const QUICK_OPTIONS: QuickOpt[] = [
  { label: "🍊 Trái nào ngọt nhất?",       value: "Hôm nay có trái nào ngọt nhất không?" },
  { label: "🍋 Ít chua dưới 100k",          value: "Gợi ý trái ít chua giá dưới 100 nghìn" },
  { label: "📦 Cam còn hàng không?",        value: "Cam còn hàng không?" },
  { label: "🚚 Ship mất bao lâu?",          value: "Ship mất bao lâu?" },
  { label: "↩️ Chính sách đổi trả",         value: "Chính sách đổi trả như thế nào?" },
  { label: "🥭 Xoài hôm nay ngon không?",   value: "Xoài hôm nay có gì ngon không?" },
];

/* ─── Intent label map ────────────────────────────────── */
const INTENT_LABELS: Record<string, { text: string; cls: string }> = {
  recommendation:   { text: "🎯 Gợi ý",         cls: "bg-accent-light   text-accent" },
  available_products:{ text: "🛒 Sản phẩm",      cls: "bg-leaf-light     text-leaf"  },
  inventory_check:  { text: "📦 Tồn kho",        cls: "bg-blue-50        text-blue-600" },
  faq_shipping:     { text: "🚚 Vận chuyển",     cls: "bg-purple-50      text-purple-600"},
  faq_return:       { text: "↩️ Đổi trả",         cls: "bg-pink-50        text-pink-600" },
  faq_storage:      { text: "🧊 Bảo quản",       cls: "bg-yellow-50      text-yellow-700"},
  fallback:         { text: "💬 Chung",           cls: "bg-gray-100       text-gray-500" },
};

function IntentBadge({ intent, confidence }: { intent: string; confidence?: number }) {
  const info = INTENT_LABELS[intent] ?? { text: intent, cls: "bg-gray-100 text-gray-500" };
  return (
    <span className={`mt-1.5 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${info.cls}`}>
      {info.text}
      {confidence != null && (
        <span className="opacity-60">· {Math.round(confidence * 100)}%</span>
      )}
    </span>
  );
}

function buildSessionId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return String(Date.now());
}

/* ─── Main component ──────────────────────────────────── */
export function ChatPanel() {
  const [sessionId, setSessionId] = useState<string>("session-tam");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "Xin chào! 👋 Mình là trợ lý tư vấn hoa quả tươi. Bạn muốn tìm trái ngọt, ít chua hay theo ngân sách?",
    },
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);
  const bottomRef           = useRef<HTMLDivElement>(null);
  const inputRef            = useRef<HTMLInputElement>(null);

  // Tự cuộn xuống khi có tin nhắn mới
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    setSessionId(buildSessionId());
  }, []);

  const canSend = input.trim().length > 0 && !loading;

  const lastProducts = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].products?.length) return messages[i].products as Product[];
    }
    return [];
  }, [messages]);

  async function submitMessage(rawMessage: string) {
    const message = rawMessage.trim();
    if (!message || loading) return;

    setError(null);
    setInput("");
    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: "user", text: message }]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendChatMessage({
        user_id: "demo-user",
        session_id: sessionId,
        message,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: res.trace_id,
          role: "assistant",
          text: res.answer,
          intent: res.intent,
          confidence: res.confidence,
          products: res.products,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Có lỗi xảy ra, vui lòng thử lại.");
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1.35fr,1fr] lg:items-stretch">

      {/* ── Cột chat ───────────────────────────────────── */}
      <section className="glass-card flex h-[72vh] min-h-[560px] max-h-[760px] flex-col overflow-hidden rounded-3xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-accent/15 bg-gradient-to-r from-accent/8 to-accent-2/8 px-5 py-3.5">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-2 text-xl shadow-md">
              🍊
              <span className="status-pulse absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-white bg-leaf" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-ink">Trợ lý Hoa Quả Tươi</h2>
              <p className="text-xs text-ink/45">Đang hoạt động · Phản hồi tức thì</p>
            </div>
          </div>
          <span className="rounded-full bg-white/75 px-3 py-1 text-[11px] font-mono font-medium text-ink/50 shadow-sm">
            #{sessionId.slice(0, 6).toUpperCase()}
          </span>
        </div>

        {/* Messages */}
        <div className="flex-1 space-y-3 overflow-y-auto overscroll-contain px-4 py-4">
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 14, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ type: "spring", stiffness: 320, damping: 28 }}
                className={`flex items-end gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                {/* Bot avatar */}
                {msg.role === "assistant" && (
                  <div className="mb-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-2 text-sm shadow-sm">
                    🍊
                  </div>
                )}

                <div className={`max-w-[78%]`}>
                  {/* Bubble */}
                  <div
                    className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "rounded-br-sm bg-gradient-to-br from-accent to-accent-2 text-white shadow-glow"
                        : "rounded-bl-sm border border-accent/10 bg-white/90 text-ink shadow-card"
                    }`}
                  >
                    {msg.text}
                  </div>

                  {/* Intent badge */}
                  {msg.role === "assistant" && msg.intent && (
                    <IntentBadge intent={msg.intent} confidence={msg.confidence} />
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-end gap-2"
            >
              <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-2 text-sm shadow-sm">
                🍊
              </div>
              <div className="rounded-2xl rounded-bl-sm border border-accent/10 bg-white/90 px-4 py-3 shadow-card">
                <div className="flex items-center gap-1.5">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Quick replies */}
        <div className="px-4 pt-1">
          <QuickReplies options={QUICK_OPTIONS} onPick={submitMessage} disabled={loading} />
        </div>

        {/* Input bar */}
        <div className="border-t border-accent/10 bg-white/55 px-3 py-3">
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => { e.preventDefault(); void submitMessage(input); }}
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ví dụ: Có trái nào ít chua dưới 100k không?"
              className="flex-1 rounded-xl border border-accent/25 bg-white/85 px-4 py-2.5 text-sm text-ink outline-none transition focus:border-accent/55 focus:ring-2 focus:ring-accent/18"
            />
            <button
              type="submit"
              disabled={!canSend}
              className="btn-send flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl text-white disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none disabled:hover:scale-100"
              aria-label="Gửi tin nhắn"
            >
              {/* Send icon */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M3.105 2.289a.75.75 0 00-.826.95l1.903 6.557H13.5a.75.75 0 010 1.5H4.182l-1.903 6.557a.75.75 0 00.826.95 28.896 28.896 0 0015.293-7.154.75.75 0 000-1.115A28.897 28.897 0 003.105 2.289z" />
              </svg>
            </button>
          </form>

          {error && (
            <p className="mt-2 flex items-center gap-1 text-xs text-red-600">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3 flex-shrink-0">
                <path fillRule="evenodd" d="M8 15A7 7 0 108 1a7 7 0 000 14zm0-10a.75.75 0 01.75.75v4a.75.75 0 01-1.5 0v-4A.75.75 0 018 5zm0 7.5a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              {error}
            </p>
          )}
        </div>
      </section>

      {/* ── Cột sản phẩm ──────────────────────────────── */}
      <section className="glass-card flex h-[420px] flex-col overflow-hidden rounded-3xl lg:h-[72vh] lg:min-h-[560px] lg:max-h-[760px]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-leaf/15 bg-gradient-to-r from-leaf/8 to-leaf/4 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🛒</span>
            <div>
              <h3 className="text-sm font-bold text-ink">Sản phẩm được gợi ý</h3>
              <p className="text-xs text-ink/45">Cập nhật theo cuộc trò chuyện</p>
            </div>
          </div>
          {lastProducts.length > 0 && (
            <motion.span
              key={lastProducts.length}
              initial={{ scale: 0.7, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="rounded-full bg-leaf-light px-2.5 py-0.5 text-xs font-bold text-leaf"
            >
              {lastProducts.length} sản phẩm
            </motion.span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto overscroll-contain p-4">
          <AnimatePresence mode="wait">
            {lastProducts.length > 0 ? (
              <motion.div
                key="products"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-3"
              >
                {lastProducts.map((product, i) => (
                  <motion.div
                    key={product.id}
                    initial={{ opacity: 0, y: 18, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0,  scale: 1    }}
                    transition={{ delay: i * 0.08, type: "spring", stiffness: 280, damping: 24 }}
                  >
                    <ProductCard product={product} />
                  </motion.div>
                ))}
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex min-h-[280px] flex-col items-center justify-center text-center"
              >
                <div className="mb-4 text-6xl float-1">🥭</div>
                <p className="text-sm font-semibold text-ink/55">Chưa có gợi ý nào</p>
                <p className="mt-1 max-w-[200px] text-xs text-ink/38 leading-relaxed">
                  Hỏi chatbot{" "}
                  <span className="font-semibold text-accent/70">"Hôm nay có gì ngọt?"</span>{" "}
                  để xem sản phẩm tươi ngon
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>
    </div>
  );
}

