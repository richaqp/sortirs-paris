import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

export function formatDateRange(start: string, end: string | null): string {
  const s = parseISO(start);
  if (!end || end === start) {
    return format(s, "EEEE d 'de' MMMM", { locale: es });
  }
  const e = parseISO(end);
  if (s.getMonth() === e.getMonth()) {
    return `${format(s, "d", { locale: es })}–${format(e, "d 'de' MMMM", { locale: es })}`;
  }
  return `${format(s, "d MMM", { locale: es })} – ${format(e, "d MMM", { locale: es })}`;
}

export function formatWeekRange(start: string, end: string): string {
  return `${format(parseISO(start), "d MMM", { locale: es })} – ${format(parseISO(end), "d MMM yyyy", { locale: es })}`;
}
