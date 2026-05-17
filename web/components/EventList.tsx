"use client";

import { useState } from "react";
import { EventCard } from "./EventCard";
import { FilterBar } from "./FilterBar";
import type { CuratedEvent } from "@/lib/types";

export function EventList({ events }: { events: CuratedEvent[] }) {
  const [filtered, setFiltered] = useState(events);

  return (
    <div className="space-y-6">
      <FilterBar events={events} onFilter={setFiltered} />
      {filtered.length === 0 && (
        <p className="text-slate-500 text-center py-12">
          No hay eventos con ese filtro esta semana.
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((event) => (
          <EventCard key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
}
