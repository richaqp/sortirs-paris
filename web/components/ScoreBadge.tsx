import { cn } from "@/lib/utils";

export function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 9
      ? "bg-emerald-500 text-white"
      : score >= 7
      ? "bg-amber-400 text-white"
      : "bg-slate-400 text-white";

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center w-9 h-9 rounded-full text-sm font-bold shrink-0",
        color
      )}
    >
      {score}
    </span>
  );
}
