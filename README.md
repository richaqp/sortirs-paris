# 🗼 Sortir à Paris

Agente semanal que scrapea ~560 eventos en París, los cura con Claude AI según el perfil familiar, y los publica en una web app personalizada.

## Cómo funciona

```
Cada domingo 8am (París)
      ↓
Scraping: ParisData + Ticketmaster + Viparis (~560 eventos)
      ↓
Scoring: Claude Haiku 4.5 con ejemplos reales de la familia
      ↓
Top 20 → JSON en GitHub → Vercel auto-deploy
      ↓
Todos los eventos → Notion (archivo histórico)
```

## Deploy en Vercel (5 minutos)

1. Ir a **https://vercel.com/new**
2. Iniciar sesión con GitHub
3. Importar el repo `richaqp/sortirs-paris`
4. En configuración del proyecto:
   - **Root Directory**: `web`
   - **Framework**: Next.js (auto-detectado)
5. Click **Deploy**

La URL será algo como `sortirs-paris.vercel.app`.

A partir de ahí, cada push a `main` en GitHub dispara un re-deploy automático.
El cron del domingo sube el JSON → Vercel lo detecta → la web se actualiza.

## Estructura del proyecto

```
sortirsParis/
  agent/
    sources/          # Scrapers: parisdata, ticketmaster, viparis
    scoring/          # Claude scorer + scorer por reglas
    publisher/        # JSON writer + GitHub API publisher
    models.py         # Modelo Event
    notion_writer.py  # Escribe a Notion
    orchestrator.py   # Pipeline principal
  profiles/
    liked_events.yaml # Eventos que la familia disfrutó (referencia del scorer)
  prompts/
    scorer_system.md  # System prompt de Claude (incluye ejemplos reales)
  scripts/
    run_weekly.py     # CLI: scrape → score → notion → github → vercel
  web/                # Next.js app (desplegada en Vercel)
    app/              # Páginas
    components/       # EventCard, FilterBar, ScoreBadge, etc.
    content/weeks/    # JSONs semanales (generados por el agente)
    lib/              # Types, data loaders, formatters
```

## Variables de entorno (.env)

```
NOTION_TOKEN=ntn_...
NOTION_DATABASE_ID=...
TICKETMASTER_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
GIT_REPO_URL=https://github.com/richaqp/sortirs-paris.git
```

## Uso local

```bash
# Setup
python3 -m venv .venv
.venv/bin/pip install httpx beautifulsoup4 lxml pydantic python-dotenv \
  tenacity dateparser "eval_type_backport>=0.2" anthropic isoweek

# Dry run (no escribe a Notion ni GitHub)
.venv/bin/python scripts/run_weekly.py --dry-run

# Run completo
.venv/bin/python scripts/run_weekly.py

# Rango específico
.venv/bin/python scripts/run_weekly.py --start 2026-06-01 --end 2026-06-08
```

## Personalizar el scorer

Editar `profiles/liked_events.yaml` y `prompts/scorer_system.md` para afinar las preferencias de la familia. El scorer usa eventos reales del pasado como referencia dorada.

## Cron remoto

El agente corre automáticamente cada **domingo a las 6am UTC (8am París)** via Claude Code Routines. Ver/gestionar: https://claude.ai/code/routines/trig_01GrSs7j6oy7k9XtXrQ8CbGY
