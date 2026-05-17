import type { Product } from "@/lib/api-client";

type ProductCardProps = { product: Product };

/* Map tên → emoji đại diện */
const FRUIT_EMOJI_MAP: [string, string][] = [
  ["xoài",       "🥭"],
  ["cam",        "🍊"],
  ["táo",        "🍎"],
  ["nho",        "🍇"],
  ["dâu tây",    "🍓"],
  ["dâu",        "🍓"],
  ["chuối",      "🍌"],
  ["dứa",        "🍍"],
  ["thơm",       "🍍"],
  ["mít",        "🌿"],
  ["bưởi",       "🍋"],
  ["chanh",      "🍋"],
  ["thanh long", "🐉"],
  ["vải",        "🍒"],
  ["chôm chôm",  "🌺"],
  ["sapoche",    "🟤"],
  ["ổi",         "🟢"],
  ["mận",        "🟣"],
];

function getFruitEmoji(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, emoji] of FRUIT_EMOJI_MAP) {
    if (lower.includes(key)) return emoji;
  }
  return "🍑";
}

function AttributeBar({
  label,
  value,
  colorFrom,
  colorTo,
}: {
  label: string;
  value: number;
  colorFrom: string;
  colorTo: string;
}) {
  const pct = Math.min(100, (value / 10) * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-ink/55">{label}</span>
        <span className="font-bold text-ink/75">{value}/10</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink/8">
        <div
          className="bar-fill h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(to right, ${colorFrom}, ${colorTo})`,
          }}
        />
      </div>
    </div>
  );
}

export function ProductCard({ product }: ProductCardProps) {
  const emoji   = getFruitEmoji(product.name);
  const inStock = product.stock > 0;

  return (
    <article className="product-card overflow-hidden rounded-2xl border border-accent/12 bg-white shadow-card">
      {/* Gradient header strip */}
      <div className="relative h-18 bg-gradient-to-br from-mellow via-accent-light to-mellow px-4 py-3">
        {/* Large fruit emoji */}
        <div className="fruit-emoji absolute -bottom-5 right-3 text-5xl drop-shadow-md">
          {emoji}
        </div>
        <div className="pr-14">
          <h3 className="font-bold leading-tight text-ink">{product.name}</h3>
          <p className="text-xs text-ink/50">{product.origin} · {product.season}</p>
        </div>
      </div>

      <div className="mt-6 px-4 pb-4 pt-1">
        {/* Stock badge */}
        <div className="mb-2">
          {inStock ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-leaf-light px-2.5 py-0.5 text-xs font-semibold text-leaf">
              <span className="status-pulse inline-block h-1.5 w-1.5 rounded-full bg-leaf" />
              Còn {product.stock} sản phẩm
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-500">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-400" />
              Hết hàng
            </span>
          )}
        </div>

        {/* Mô tả */}
        <p className="mb-3 line-clamp-2 text-xs leading-relaxed text-ink/60">
          {product.description}
        </p>

        <div className="mb-3 flex flex-wrap gap-1.5 text-[11px]">
          <span className="rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-700">
            Màu: {product.color}
          </span>
          <span className="rounded-full bg-sky-50 px-2 py-0.5 font-medium text-sky-700">
            {product.calories_per_100g} kcal/100g
          </span>
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
            Bảo quản: {product.shelf_life_days} ngày
          </span>
        </div>

        {/* Attribute bars */}
        <div className="mb-4 space-y-2.5">
          <AttributeBar
            label="Độ ngọt"
            value={product.sweetness_level}
            colorFrom="#f5a623"
            colorTo="#f06322"
          />
          <AttributeBar
            label="Độ chua"
            value={product.sourness_level}
            colorFrom="#e91e8c"
            colorTo="#c0392b"
          />
          <AttributeBar
            label="Độ hạt"
            value={product.seed_level}
            colorFrom="#52c178"
            colorTo="#2d9555"
          />
          <AttributeBar
            label="Mọng nước"
            value={product.juiciness_level}
            colorFrom="#29b6f6"
            colorTo="#039be5"
          />
          <AttributeBar
            label="Độ thơm"
            value={product.aroma_level}
            colorFrom="#ffca28"
            colorTo="#ff8f00"
          />
        </div>

        <p className="mb-3 rounded-lg bg-ink/5 px-2.5 py-1.5 text-[11px] text-ink/65">
          Gợi ý dùng: <span className="font-semibold text-ink/80">{product.best_use}</span>
        </p>

        {/* Price + CTA */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-ink/40">Giá bán</p>
            <p className="gradient-text text-xl font-bold leading-tight">
              {product.price.toLocaleString("vi-VN")}₫
            </p>
          </div>
          <button
            type="button"
            disabled={!inStock}
            className="rounded-xl bg-gradient-to-r from-accent to-accent-2 px-4 py-2 text-xs font-bold text-white shadow-md transition-all duration-200 hover:scale-105 hover:shadow-glow active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100 disabled:hover:shadow-none"
          >
            {inStock ? "Đặt ngay 🛒" : "Hết hàng"}
          </button>
        </div>
      </div>
    </article>
  );
}

