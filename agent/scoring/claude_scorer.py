from __future__ import annotations
import asyncio
import json
import re
from pathlib import Path

import anthropic

from agent.models import Event
from agent.scoring.models import ScoredEvent, CuratedEvent, WeekData

_SYSTEM_PROMPT = (Path(__file__).parent.parent.parent / "prompts" / "scorer_system.md").read_text()
_BATCH_SIZE = 10
_MAX_CONCURRENCY = 5
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


def _parse_response(text: str) -> list[ScoredEvent]:
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    data = json.loads(text)
    return [ScoredEvent(**r) for r in data["results"]]


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
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=1024,
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
            except Exception as exc:
                print(f"  [scorer] batch error: {exc}")
                # Return neutral scores so the pipeline doesn't break
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
