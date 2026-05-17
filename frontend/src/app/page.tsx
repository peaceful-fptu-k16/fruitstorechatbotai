import { ChatPanel } from "@/components/chat-panel";

const FLOATING_FRUITS = [
  { emoji: "🍊", cls: "float-1", left: "6%",  top: "8%",  size: 38 },
  { emoji: "🥭", cls: "float-2", left: "18%", top: "72%", size: 46 },
  { emoji: "🍋", cls: "float-3", left: "82%", top: "12%", size: 34 },
  { emoji: "🍇", cls: "float-4", left: "90%", top: "60%", size: 40 },
  { emoji: "🍓", cls: "float-5", left: "50%", top: "5%",  size: 30 },
  { emoji: "🍍", cls: "float-6", left: "70%", top: "82%", size: 44 },
  { emoji: "🫐", cls: "float-7", left: "35%", top: "88%", size: 32 },
  { emoji: "🍎", cls: "float-8", left: "3%",  top: "45%", size: 36 },
];

export default function HomePage() {
  return (
    <main className="relative mx-auto min-h-screen w-full max-w-7xl px-4 py-10 md:px-8 md:py-14">

      {/* ── Floating fruit decorations ────────────────── */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 overflow-hidden">
        {FLOATING_FRUITS.map((f) => (
          <span
            key={f.emoji + f.left}
            className={`absolute select-none ${f.cls}`}
            style={{ left: f.left, top: f.top, fontSize: f.size, opacity: 0.18 }}
          >
            {f.emoji}
          </span>
        ))}
      </div>

      {/* ── Hero ──────────────────────────────────────── */}
      <header className="page-in mb-10 text-center">
        {/* Online badge */}
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent-light px-4 py-1.5 text-sm font-semibold text-accent shadow-sm">
          <span className="status-pulse inline-block h-2.5 w-2.5 rounded-full bg-leaf" />
          Chatbot AI · Đang hoạt động
        </div>

        {/* Headline */}
        <h1 className="mb-4 text-4xl font-bold leading-tight tracking-tight md:text-6xl lg:text-7xl">
          <span className="gradient-text">Trái Cây Tươi</span>
          <br />
        </h1>
      </header>

      {/* ── Chat panel ────────────────────────────────── */}
      <div className="page-in-d2">
        <ChatPanel />
      </div>

      {/* ── Footer ────────────────────────────────────── */}
      <footer className="page-in-d4 mt-10 text-center text-xs text-ink/35">
        Được xây dựng với{" "}
        <span className="font-semibold text-accent/60">FastAPI</span> ·{" "}
        <span className="font-semibold text-accent/60">Next.js</span> ·{" "}
        <span className="font-semibold text-accent/60">RAG</span> ·{" "}
        <span className="font-semibold text-accent/60">SQLAlchemy</span>
        &nbsp;•&nbsp; Dữ liệu demo, chỉ mang tính minh họa
      </footer>
    </main>
  );
}

