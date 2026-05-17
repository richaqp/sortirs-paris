from __future__ import annotations
import asyncio
import json
import re
import time
from pathlib import Path

import anthropic

from agent.models import Event
from agent.scoring.models import ScoredEvent, CuratedEvent, WeekData

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
_SYSTEM_PROMPT = (_PROMPTS_DIR / "scorer_system.md").read_text()
_BATCH_SIZE = 5          # smaller batches → less output tokens per call
_MAX_CONCURRENCY = 2    # Tier 1 new accounts: strict concurrent connection limit
_MAX_TOKENS = 2048      # enough for 5 events × ~300 tokens each
_MODEL = "claude-haiku-4-5"


def _event_to_dict(ev: Event, idx: int) -> dict:
    return {
        "id": f"ev_{idx:04d}",
        "titulo": ev.evento,
        "fecha": str(ev.fecha_inicio),
        "lugar": ev.lugar,
        "costo": ev.costo,
        "tipo": ev.tipo_publico,
        "fuente": ev.fuente,
    }


def _normalize_result(r: dict) -> dict:
    """Normalize field name variations Claude might use."""
    # Normalize razon (handles accented variants)
    for alt in ("razón", "reason", "descripcion", "descripción", "explanation"):
        if alt in r and "razon" not in r:
            r["razon"] = r.pop(alt)
    r.setdefault("razon", "Sin descripción disponible.")
    r.setdefault("titulo_es", r.get("titulo", ""))
    r.setdefault("tags", [])
    return r


def _parse_response(text: str) -> list[ScoredEvent]:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    data = json.loads(text)
    return [ScoredEvent(**_normalize_result(r)) for r in data["results"]]


class ClaudeScorer:
    def __init__(self, api_key: str, model: str = _MODEL):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def _score_batch(
        self,
        batch: list[tuple[int, Event]],
        semaphore: asyncio.Semaphore,
    ) -> list[ScoredEvent]:
        payload = [_event_to_dict(ev, idx) for idx, ev in batch]
        user_msg = f"Evalúa estos {len(payload)} eventos:\n\n{json.dumps(payload, ensure_ascii=False, indent=2)}"

        async with semaphore:
            for attempt in range(3):
                try:
                    response = await self._client.messages.create(
                        model=self._model,
                        max_tokens=_MAX_TOKENS,
                        system=[
                            {
                                "type": "text",
                                "text": _SYSTEM_PROMPT,
                                "cache_control": {"type": "ephemeral"},
                            }
                        ],
                        messages=[{"role": "user", "content": user_msg}],
                    )
                    return _parse_response(response.content[0].text)
                except anthropic.RateLimitError:
                    wait = 30 * (attempt + 1)
                    print(f"  [scorer] rate limit — esperando {wait}s…")
                    await asyncio.sleep(wait)
                except Exception as exc:
                    print(f"  [scorer] batch error: {exc}")
                    break
            # Fallback: return zero scores so pipeline doesn't break
            return [
                ScoredEvent(id=f"ev_{idx:04d}", score=0, titulo_es=ev.evento,
                            razon="Error al evaluar.", tags=[])
                for idx, ev in batch
            ]

    async def score_all(self, events: list[Event]) -> list[ScoredEvent]:
        indexed = list(enumerate(events))
        batches = [indexed[i:i + _BATCH_SIZE] for i in range(0, len(indexed), _BATCH_SIZE)]
        semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

        tasks = [self._score_batch(batch, semaphore) for batch in batches]
        results = await asyncio.gather(*tasks)

        flat: list[ScoredEvent] = []
        for batch_result in results:
            flat.extend(batch_result)
        return flat

    def merge(
        self,
        events: list[Event],
        scored: list[ScoredEvent],
        top_k: int = 20,
    ) -> list[CuratedEvent]:
        score_map = {s.id: s for s in scored}

        curated: list[CuratedEvent] = []
        for idx, ev in enumerate(events):
            ev_id = f"ev_{idx:04d}"
            s = score_map.get(ev_id)
            if s is None or s.score < 5:
                continue
            curated.append(CuratedEvent(
                id=ev_id,
                titulo_fr=ev.evento,
                titulo_es=s.titulo_es,
                fecha_inicio=ev.fecha_inicio,
                fecha_fin=ev.fecha_fin,
                lugar=ev.lugar,
                costo=ev.costo,
                tipo_publico=ev.tipo_publico,
                link=ev.link,
                imagen=ev.imagen,
                fuente=ev.fuente,
                score=s.score,
                razon=s.razon,
                tags=s.tags,
            ))

        curated.sort(key=lambda e: e.score, reverse=True)
        return curated[:top_k]
