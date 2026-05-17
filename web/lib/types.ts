export type CuratedEvent = {
  id: string;
  titulo_fr: string;
  titulo_es: string;
  fecha_inicio: string;
  fecha_fin: string | null;
  lugar: string;
  costo: string;
  tipo_publico: string;
  link: string;
  imagen: string | null;
  fuente: "parisdata" | "ticketmaster" | "viparis" | "manual";
  score: number;
  razon: string;
  tags: string[];
  disponibilidad: string | null;
};

export type WeekData = {
  week_id: string;
  range_start: string;
  range_end: string;
  generated_at: string;
  total_scraped: number;
  total_scored: number;
  events: CuratedEvent[];
};
