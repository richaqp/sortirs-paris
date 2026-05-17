from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel

Tag = Literal[
    "aire-libre", "musica", "ciencia", "hispano", "familia",
    "teen", "nina", "taller", "gratis", "museo", "deporte", "festival",
]


class ScoredEvent(BaseModel):
    id: str
    score: int
    titulo_es: str = ""
    razon: str = ""
    tags: list[str] = []


class CuratedEvent(BaseModel):
    id: str
    titulo_fr: str
    titulo_es: str
    fecha_inicio: date
    fecha_fin: date | None = None
    lugar: str
    costo: str
    tipo_publico: str
    link: str
    imagen: str | None = None
    fuente: str
    score: int
    razon: str
    tags: list[str]


class WeekData(BaseModel):
    week_id: str
    range_start: date
    range_end: date
    generated_at: str
    total_scraped: int
    total_scored: int
    events: list[CuratedEvent]
