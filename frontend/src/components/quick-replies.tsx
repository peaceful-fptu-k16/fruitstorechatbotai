type QuickOpt = { label: string; value: string } | string;

type QuickRepliesProps = {
  options: QuickOpt[];
  onPick: (message: string) => void;
  disabled?: boolean;
};

export function QuickReplies({ options, onPick, disabled }: QuickRepliesProps) {
  return (
    <div className="flex flex-wrap gap-1.5 pb-2 pt-1">
      {options.map((opt, i) => {
        const label = typeof opt === "string" ? opt : opt.label;
        const value = typeof opt === "string" ? opt : opt.value;
        return (
          <button
            key={i}
            type="button"
            onClick={() => onPick(value)}
            disabled={disabled}
            className="chip animate-scaleIn rounded-full border border-accent/28 bg-white/80 px-3 py-1.5 text-xs font-medium text-ink/75 shadow-sm hover:border-accent hover:bg-accent-light hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"
            style={{ animationDelay: `${i * 55}ms` }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

