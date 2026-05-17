import { loadCurrentWeek, listWeeks } from "@/lib/data";
import { formatWeekRange } from "@/lib/formatDate";
import { EventList } from "@/components/EventList";
import Link from "next/link";

export const revalidate = 3600;

export default function Home() {
  const week = loadCurrentWeek();

  if (!week) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-500">
          Aún no hay eventos cargados. El agente corre cada domingo a las 8am.
        </p>
      </main>
    );
  }

  const pastWeeks = listWeeks().filter((w) => w !== week.week_id);

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="font-bold text-lg text-slate-900">
              🗼 Sortir à Paris
            </h1>
            <p className="text-xs text-slate-500">
              Top {week.events.length} de {week.total_scraped} eventos
            </p>
          </div>
          {pastWeeks.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 hidden sm:block">
                Semanas anteriores:
              </span>
              <div className="flex gap-1">
                {pastWeeks.slice(0, 3).map((w) => (
                  <Link
                    key={w}
                    href={`/semana/${w}`}
                    className="text-xs px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
                  >
                    {w}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Hero */}
      <div className="bg-gradient-to-br from-blue-600 to-indigo-700 text-white">
        <div className="max-w-6xl mx-auto px-4 py-10">
          <p className="text-blue-200 text-sm font-medium uppercase tracking-wide mb-1">
            Esta semana en París
          </p>
          <h2 className="text-3xl font-bold mb-2">
            {formatWeekRange(week.range_start, week.range_end)}
          </h2>
          <p className="text-blue-200 text-sm">
            Curado por IA para tu familia · generado el{" "}
            {new Date(week.generated_at).toLocaleDateString("es-ES", {
              weekday: "long",
              day: "numeric",
              month: "long",
            })}
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        <EventList events={week.events} />
      </div>
    </main>
  );
}
