"use client";

const TAG_COLORS: Record<string, string> = {
  hispano: "bg-red-100 text-red-700 hover:bg-red-200",
  musica: "bg-purple-100 text-purple-700 hover:bg-purple-200",
  ciencia: "bg-blue-100 text-blue-700 hover:bg-blue-200",
  "aire-libre": "bg-green-100 text-green-700 hover:bg-green-200",
  taller: "bg-orange-100 text-orange-700 hover:bg-orange-200",
  festival: "bg-pink-100 text-pink-700 hover:bg-pink-200",
  gratis: "bg-emerald-100 text-emerald-700 hover:bg-emerald-200",
  familia: "bg-sky-100 text-sky-700 hover:bg-sky-200",
  teen: "bg-violet-100 text-violet-700 hover:bg-violet-200",
  nina: "bg-rose-100 text-rose-700 hover:bg-rose-200",
  inmersivo: "bg-indigo-100 text-indigo-700 hover:bg-indigo-200",
  "salon-publico": "bg-yellow-100 text-yellow-700 hover:bg-yellow-200",
  gastronomia: "bg-amber-100 text-amber-700 hover:bg-amber-200",
};

const TAG_LABELS: Record<string, string> = {
  hispano: "🎵 hispano",
  musica: "🎶 música",
  ciencia: "🔬 ciencia",
  "aire-libre": "🌿 aire libre",
  taller: "🎨 taller",
  festival: "🎪 festival",
  gratis: "✨ gratis",
  familia: "👨‍👩‍👧 familia",
  teen: "🧑 teen",
  nina: "👧 niña",
  inmersivo: "🌀 inmersivo",
  "salon-publico": "🏛 salón",
  gastronomia: "🍫 gastronomía",
  deporte: "⚽ deporte",
  museo: "🖼 museo",
};

export function TagPill({
  tag,
  active,
  onClick,
}: {
  tag: string;
  active?: boolean;
  onClick?: () => void;
}) {
  const base =
    TAG_COLORS[tag] ?? "bg-slate-100 text-slate-600 hover:bg-slate-200";
  const label = TAG_LABELS[tag] ?? tag;

  return (
    <button
      onClick={onClick}
      className={`text-xs px-2 py-0.5 rounded-full font-medium transition-all cursor-pointer ${base} ${
        active ? "ring-2 ring-offset-1 ring-current" : ""
      }`}
    >
      {label}
    </button>
  );
}
