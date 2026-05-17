import { loadWeek, listWeeks } from "@/lib/data";
import { formatWeekRange } from "@/lib/formatDate";
import { EventList } from "@/components/EventList";
import Link from "next/link";
import { notFound } from "next/navigation";

export const revalidate = 3600;

export async function generateStaticParams() {
  return listWeeks().map((slug) => ({ slug }));
}

export default async function SemanaPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const week = loadWeek(slug);
  if (!week) notFound();

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
          <Link
            href="/"
            className="text-sm text-slate-500 hover:text-slate-800 transition-colors"
          >
            ← Semana actual
          </Link>
          <span className="text-slate-300">|</span>
          <h1 className="font-bold text-slate-900">🗼 Sortir à Paris</h1>
        </div>
      </header>

      <div className="bg-gradient-to-br from-slate-600 to-slate-800 text-white">
        <div className="max-w-6xl mx-auto px-4 py-10">
          <p className="text-slate-400 text-sm font-medium uppercase tracking-wide mb-1">
            Archivo — {week.week_id}
          </p>
          <h2 className="text-3xl font-bold mb-2">
            {formatWeekRange(week.range_start, week.range_end)}
          </h2>
          <p className="text-slate-400 text-sm">
            {week.total_scored} eventos curados de {week.total_scraped}{" "}
            scrapeados
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        <EventList events={week.events} />
      </div>
    </main>
  );
}
