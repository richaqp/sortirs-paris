from __future__ import annotations
import re
from agent.models import Event
from agent.scoring.models import ScoredEvent, CuratedEvent

# ── Intereses (cada match suma puntos) ──────────────────────────────────────
_INTERESTS: list[tuple[str, list[str], str]] = [
    # (tag, keywords, label_es)
    ("ciencia", [
        "science", "scientif", "planétarium", "planétarium", "astronomi",
        "robot", "technologi", "stem", "informatique", "cité des sciences",
        "découverte", "expérience", "chimie", "physique", "mathémat",
        "numérique", "innovation", "invention", "espace", "dinosaur",
    ], "ciencia"),
    ("aire-libre", [
        "plein air", "outdoor", "parc", "jardin", "nature", "forêt",
        "vélo", "balade", "randonnée", "acrobranche", "escalade",
        "aventure", "pique-nique", "promenade", "bois de", "bassin",
        "bord de", "berge", "seine", "canal",
    ], "aire libre"),
    ("musica", [
        "concert", "festival de musique", "festival musical", "musique live",
        "spectacle musical", "orchestre", "fanfare", "chorale",
        "rap", "jazz", "pop", "rock", "world music",
    ], "música en vivo"),
    ("hispano", [
        "flamenco", "salsa", "tango", "latin", "latino", "latina",
        "espagnol", "espanol", "hispanic", "reggaeton", "cumbia",
        "merengue", "bachata", "mariachi", "brésil", "brasil",
        "amérique latine", "amérique du sud", "mexique",
    ], "cultura hispana"),
    ("taller", [
        "atelier", "workshop", "stage", "création", "fabriquer",
        "bricolage", "dessin", "peinture", "sculpture", "poterie",
        "cuisine", "initiation", "apprentissage", "découverte pratique",
    ], "talleres creativos"),
    ("museo", [
        "musée", "exposition", "galerie", "patrimoine", "histoire",
        "archéologie", "beaux-arts", "culture",
    ], "exposición cultural"),
    ("deporte", [
        "sport", "football", "basket", "tennis", "natation", "gym",
        "athlétisme", "handball", "rugby", "tournoi", "compétition",
        "match", "sportif",
    ], "deporte"),
    ("festival", [
        "festival", "fête", "foire", "braderie", "marché de noël",
        "carnaval", "parade",
    ], "festival"),
    ("nina", [
        "enfant", "enfants", "famille", "kids", "junior", "petits",
        "jeunesse", "pour les enfants", "parents", "bébé", "maternelle",
    ], "niños"),
    ("teen", [
        "ado", "adolescent", "jeune", "teen", "15-25", "young",
        "lycée", "collège",
    ], "adolescentes"),
]

# ── Anti-patrones → score máximo 2 ──────────────────────────────────────────
_ANTI_PATTERNS = [
    r"\bréservé aux professionnels\b",
    r"\bprofessionnel(le)?s? uniquement\b",
    r"\bb2b\b",
    r"\bfranchis",
    r"\bmobilier\b",
    r"\béquipement industriel\b",
    r"\bcongr[eè]s\b.*\bprofess",
    r"\bsalon\b.*\bprofess",   # "salon professionnel" pero NO "salon du chocolat"
    r"\bsommet\b.*\bchefs?\b",
    r"\bconférence\b.*\bexpert",
    r"\bexclusiv.*\badulte",
    r"\b18\+\b",
    r"\binterdit.*mineur",
]

# Salones grand public que SON bienvenidos (override anti-pattern)
_SALON_GRAND_PUBLIC = [
    "chocolat", "agriculture", "gastronomie", "livre", "bande dessinée",
    "jeux", "jouet", "jardin", "bien-être", "musique", "enfant",
    "famille", "créat", "art", "photo",
]

# ── Razones en español según tags ────────────────────────────────────────────
_RAZON_TEMPLATES: dict[frozenset, str] = {
    frozenset(["ciencia", "taller"]): "Talleres científicos hands-on — las dos hijas aprenden haciendo. Difícil que se aburran.",
    frozenset(["ciencia", "nina"]): "Exposición o actividad científica pensada para niños: perfecta para tu hija más pequeña.",
    frozenset(["musica", "aire-libre"]): "Concierto al aire libre, ideal para disfrutar con toda la familia sin encierros.",
    frozenset(["musica", "festival"]): "Festival musical con buen ambiente familiar para compartir en vivo.",
    frozenset(["aire-libre", "deporte"]): "Actividad deportiva al aire libre: mueven el cuerpo y salen de la pantalla.",
    frozenset(["hispano"]): "¡Evento con sabor latino! Una oportunidad para conectar con la cultura hispanohablante en París.",
    frozenset(["taller", "nina"]): "Taller práctico y creativo pensado para niños — tu hija pequeña va a disfrutarlo mucho.",
    frozenset(["festival", "aire-libre"]): "Festival al aire libre para toda la familia. Ambiente festivo garantizado.",
}

_DEFAULT_RAZONES: dict[str, str] = {
    "ciencia": "Evento de ciencia ideal para despertar la curiosidad de las dos hijas.",
    "aire-libre": "Plan al aire libre, perfecto para desconectar y explorar juntos.",
    "musica": "Música en vivo siempre es una buena salida familiar.",
    "hispano": "Conexión con la cultura hispana/latina en el corazón de París.",
    "taller": "Taller creativo donde las hijas pueden crear y aprender con las manos.",
    "deporte": "Actividad deportiva para mantenerse activos como familia.",
    "festival": "El ambiente festivo lo hace disfrutable para todas las edades.",
    "museo": "Visita cultural bien aprovechada para las dos hijas.",
    "nina": "Actividad pensada especialmente para niños y familias.",
    "teen": "Actividad con buena energía para adolescentes.",
}


def _score_event(ev: Event) -> ScoredEvent:
    text = (ev.evento + " " + ev.lugar + " " + (ev.tipo_publico or "")).lower()

    # Check anti-patterns (but override if it's a grand public salon)
    is_grand_public_salon = any(kw in text for kw in _SALON_GRAND_PUBLIC)
    is_antipattern = (
        not is_grand_public_salon
        and any(re.search(pat, text, re.IGNORECASE) for pat in _ANTI_PATTERNS)
    )

    matched_tags: list[str] = []
    for tag, keywords, _ in _INTERESTS:
        if any(kw in text for kw in keywords):
            matched_tags.append(tag)

    # Base score
    if is_antipattern:
        score = min(2, len(matched_tags))
    else:
        score = min(10, len(matched_tags) * 2 + 1)
        # Bonus: free event
        if "gratuit" in (ev.costo or "").lower() or ev.costo == "Gratuito":
            score = min(10, score + 1)
        # Bonus: highly relevant combos
        if "ciencia" in matched_tags and "taller" in matched_tags:
            score = min(10, score + 1)
        if "aire-libre" in matched_tags and "nina" in matched_tags:
            score = min(10, score + 1)
        # Penalty: solo música clásica adulta sin componente familiar
        if matched_tags == ["musica"] and "nina" not in matched_tags and "teen" not in matched_tags:
            score = max(4, score - 1)
        # Penalty: no relevant tags at all
        if not matched_tags:
            score = max(0, score - 3)

    # Generate razon
    tag_set = frozenset(matched_tags)
    razon = ""
    for key_tags, text_razon in _RAZON_TEMPLATES.items():
        if key_tags <= tag_set:
            razon = text_razon
            break
    if not razon:
        for tag in ["ciencia", "hispano", "aire-libre", "musica", "taller", "deporte", "festival", "nina"]:
            if tag in tag_set:
                razon = _DEFAULT_RAZONES[tag]
                break
    if not razon:
        razon = "Evento cultural en París que puede ser interesante para la familia."

    if is_antipattern:
        razon = "Evento principalmente profesional o B2B, poco relevante para la familia."

    idx = 0  # placeholder; real id set in score_all
    return ScoredEvent(
        id="",
        score=score,
        titulo_es=ev.evento,  # same as FR — no translation without Claude API
        razon=razon,
        tags=matched_tags,
    )


class EventScorer:
    """Rules-based scorer — no API key required."""

    async def score_all(self, events: list[Event]) -> list[ScoredEvent]:
        results = []
        for idx, ev in enumerate(events):
            scored = _score_event(ev)
            scored.id = f"ev_{idx:04d}"
            results.append(scored)
        return results

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
