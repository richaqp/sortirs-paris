from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel, HttpUrl, field_validator

TipoPublico = Literal["Familia", "Adolescentes", "Hispano/Latino", "Salón masivo", "Deportivo"]
Fuente = Literal["viparis", "ticketmaster", "parisdata"]


class Event(BaseModel):
    evento: str
    fecha_inicio: date
    fecha_fin: date | None = None
    lugar: str
    tipo_publico: TipoPublico
    link: str
    costo: str = "TBA"
    fuente: Fuente
    imagen: str | None = None

    @field_validator("evento", "lugar", "costo", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    def fecha_display(self) -> str:
        if self.fecha_fin and self.fecha_fin != self.fecha_inicio:
            return f"{self.fecha_inicio} → {self.fecha_fin}"
        return str(self.fecha_inicio)
