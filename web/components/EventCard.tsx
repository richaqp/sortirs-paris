import Image from "next/image";
import { ExternalLink, MapPin, Euro, Ticket, Star } from "lucide-react";
import { ScoreBadge } from "./ScoreBadge";
import { TagPill } from "./TagPill";
import { formatDateRange } from "@/lib/formatDate";
import type { CuratedEvent } from "@/lib/types";

const SOURCE_LABEL: Record<string, string> = {
  parisdata: "paris.fr",
  ticketmaster: "Ticketmaster",
  viparis: "Viparis",
  manual: "⭐ Selección manual",
};

function AvailabilityBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    "Entradas disponibles": "bg-green-100 text-green-700",
    "Sin entradas — verificar reventa": "bg-red-100 text-red-700",
    "Cancelado": "bg-slate-200 text-slate-500 line-through",
    "Postpuesto": "bg-orange-100 text-orange-700",
    "Reprogramado": "bg-yellow-100 text-yellow-700",
  };
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${styles[status] ?? "bg-slate-100 text-slate-600"}`}>
      <Ticket className="w-3 h-3" />
      {status}
    </span>
  );
}

export function EventCard({ event }: { event: CuratedEvent }) {
  const isManual = event.fuente === "manual";

  return (
    <article className={`bg-white rounded-2xl shadow-sm border overflow-hidden flex flex-col hover:shadow-md transition-shadow ${isManual ? "border-amber-200 ring-1 ring-amber-100" : "border-slate-100"}`}>
      {event.imagen && (
        <div className="relative w-full h-44 bg-slate-100">
          <Image
            src={event.imagen}
            alt={event.titulo_fr}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        </div>
      )}

      <div className="p-4 flex flex-col gap-3 flex-1">
        {/* Header: score + title */}
        <div className="flex gap-3 items-start">
          <ScoreBadge score={event.score} />
          <div className="min-w-0">
            <h2 className="font-semibold text-slate-900 leading-snug line-clamp-2">
              {event.titulo_fr}
            </h2>
            {event.titulo_es && event.titulo_es !== event.titulo_fr && (
              <p className="text-sm text-slate-500 mt-0.5 line-clamp-1">
                {event.titulo_es}
              </p>
            )}
          </div>
        </div>

        {/* Date + venue + price */}
        <div className="text-sm text-slate-600 space-y-1">
          <p className="font-medium capitalize">
            {formatDateRange(event.fecha_inicio, event.fecha_fin)}
          </p>
          <p className="flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">{event.lugar}</span>
          </p>
          <p className="flex items-center gap-1">
            <Euro className="w-3.5 h-3.5 shrink-0" />
            <span>{event.costo}</span>
          </p>
        </div>

        {/* Ticket availability (Ticketmaster events) */}
        {event.disponibilidad && (
          <div>
            <AvailabilityBadge status={event.disponibilidad} />
          </div>
        )}

        {/* Claude's reason */}
        <div className="bg-amber-50 border-l-4 border-amber-300 pl-3 pr-2 py-2 rounded-r-lg">
          <p className="text-sm text-amber-900 leading-relaxed">{event.razon}</p>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5">
          {event.tags.map((tag) => (
            <TagPill key={tag} tag={tag} />
          ))}
        </div>

        {/* Footer: source + link */}
        <div className="flex items-center justify-between mt-auto pt-1">
          <span className={`text-xs ${isManual ? "text-amber-600 font-medium" : "text-slate-400"}`}>
            {SOURCE_LABEL[event.fuente] ?? event.fuente}
          </span>
          <a
            href={event.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
          >
            Ver evento
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </article>
  );
}
