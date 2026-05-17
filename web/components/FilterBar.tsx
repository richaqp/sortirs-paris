"use client";

import { useState } from "react";
import { TagPill } from "./TagPill";
import type { CuratedEvent } from "@/lib/types";

const ALL_TAGS = [
  "gratis", "aire-libre", "hispano", "musica", "ciencia",
  "taller", "festival", "familia", "teen", "nina", "inmersivo",
];

type Props = {
  events: CuratedEvent[];
  onFilter: (filtered: CuratedEvent[]) => void;
};

export function FilterBar({ events, onFilter }: Props) {
  const [active, setActive] = useState<Set<string>>(new Set());

  const toggle = (tag: string) => {
    const next = new Set(active);
    if (next.has(tag)) next.delete(tag);
    else next.add(tag);
    setActive(next);
    if (next.size === 0) {
      onFilter(events);
    } else {
      onFilter(events.filter((e) => e.tags.some((t) => next.has(t))));
    }
  };

  const clear = () => {
    setActive(new Set());
    onFilter(events);
  };

  const presentTags = ALL_TAGS.filter((t) =>
    events.some((e) => e.tags.includes(t))
  );

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {presentTags.map((tag) => (
        <TagPill
          key={tag}
          tag={tag}
          active={active.has(tag)}
          onClick={() => toggle(tag)}
        />
      ))}
      {active.size > 0 && (
        <button
          onClick={clear}
          className="text-xs text-slate-400 hover:text-slate-600 underline ml-1"
        >
          limpiar
        </button>
      )}
    </div>
  );
}
