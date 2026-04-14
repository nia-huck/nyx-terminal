# Nyx Terminal

**Real-time economic early warning system for Argentina** — AI-powered financial intelligence dashboard with live transcription alerts, multi-source data aggregation, and autonomous risk analysis.

Built for the [Anthropic MCP Hackathon](https://anthropic.com) using **Claude AI + Model Context Protocol (MCP) + Apify**.

> **Live Demo:** [https://nyx-terminal.onrender.com](https://nyx-terminal.onrender.com)

---

## What It Does

Nyx Terminal monitors Argentina's volatile economy in real time, combining 10+ data sources into a single intelligence dashboard. It detects risks before they become headlines.

| Feature | Description |
|---------|-------------|
| **Early Warning System** | Classifies events (labor strikes, BCRA policy, devaluation signals) with urgency scoring 1-10 and geospatial tagging |
| **MCP + Apify Integration** | Real-time web, Twitter/X, Reddit, and news scraping via Model Context Protocol tools with budget guards |
| **Live Transcription & Alerts** | Monitors YouTube livestreams, extracts captions, detects economic keywords, and fires alerts in real time |
| **AI Agent (Claude)** | Three modes — Analyst, Researcher, Monitor — with tool use, PostgreSQL memory, and cost-controlled live search |
| **80+ Analysis Functions** | Dolar velocity, carry trade returns, inflation decomposition, reserves burn rate, composite Nyx Risk Index |

---

## Architecture

```
                    +-------------------+
                    |   React Frontend  |
                    |  (Liquid Glass UI) |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  FastAPI Gateway   |  :8000
                    |  (api.py)          |
                    +--+------+------+--+
                       |      |      |
              +--------+  +---+---+  +--------+
              |           |       |           |
     +--------v---+  +---v----+  +---v--------+
     | DataStore   |  | Agent  |  | Diaricat   |
     | (info/*.json)  | Claude |  | Live :8766 |
     |             |  | + MCP  |  | YT Transcr |
     +-------------+  +---+---+  +------------+
                           |
                    +------v------+
                    |  Apify MCP  |
                    |  Server     |
                    +------+------+
                           |
              +------------+------------+
              |            |            |
         +----v---+  +----v---+  +----v----+
         | Web    |  | Twitter|  | Reddit  |
         | Search |  | /X     |  | Scraper |
         +--------+  +--------+  +---------+
```

---

## Key Components

### 1. Early Warning System

The classifier (`core/classifier.py`) processes news, tweets, and articles in real time:

- **5 event categories:** Sindical (strikes/labor), Regulatorio (BCRA policy), Economico (rates/inflation), Politico (congress/fiscal), Climatico (agriculture impact)
- **Urgency scoring:** 1-10 scale based on keyword intensity, source credibility, and historical impact patterns
- **Geospatial mapping:** Events tagged to Argentine provinces with lat/lng coordinates, displayed on an interactive Leaflet map
- **Multi-source fusion:** Correlates signals across news, social media, and official data

### 2. MCP Server for Apify Queries

The MCP server (`core/mcp_apify.py`) exposes Apify actors as Model Context Protocol tools that the Claude agent can invoke autonomously:

```
MCP Tools Available:
  apify_web_search      - Real-time web search via RAG Web Browser
  apify_twitter_search  - Twitter/X scraping for financial sentiment
  apify_news_scrape     - Full article extraction from Argentine media
  apify_reddit_search   - Reddit financial community monitoring
```

**Budget guard system:** Each query has a configurable max cost (default $0.50 USD). The agent tracks cumulative spend per session and refuses additional live searches when the budget is exhausted — preventing runaway API costs.

**Cost estimates per actor:**
| Actor | Cost/Run |
|-------|----------|
| Web Search | ~$0.02 |
| Twitter/X | ~$0.05 |
| News Scrape | ~$0.03 |
| Reddit | ~$0.02 |

### 3. Live Transcription & Alert Detection

The Diaricat Live service (`diaricat_service.py`) provides real-time monitoring of YouTube livestreams:

1. **Start a stream** → POST `/v1/stream/start` with a YouTube URL
2. **Caption extraction** → Uses `youtube-transcript-api` with multi-language fallback (ES → ES-419 → EN)
3. **Keyword matching** → 30+ preconfigured economic keywords with sector tags and urgency levels:
   - `devaluacion` (urgency: 9, sector: finanzas)
   - `cepo` (urgency: 8, sector: finanzas)
   - `huelga` (urgency: 8, sector: sindical)
   - `fmi` (urgency: 8, sector: economia)
   - ...and more
4. **Alert generation** → Keyword hits produce typed alerts pushed via Server-Sent Events (SSE)
5. **Frontend display** → Real-time transcript + highlighted alerts in the Live panel

**Custom keywords:** Add/remove keywords at runtime via REST API — no restart needed.

### 4. AI Agent (NyxAgent)

Three operational modes powered by Claude:

| Mode | Behavior |
|------|----------|
| **Analyst** | Quick answers using local data. Prioritizes speed and concrete numbers. |
| **Researcher** | Deep investigation with cross-referencing. Uses Apify for fresh data. Saves insights to PostgreSQL. |
| **Monitor** | Automated anomaly detection. Compares current vs historical data. Generates risk alerts. |

The agent has access to 8 tools:
- `consultar_datos` — Query cached economic data (free, instant)
- `consultar_senales` — Compute derived signals (brecha cambiaria, tasa real, etc.)
- `consultar_analisis` — Run mathematical analysis (80+ functions)
- `buscar_db` — Full-text search on PostgreSQL context
- `guardar_contexto` — Save insights for future queries
- `busqueda_web` — Live web search via Apify MCP
- `busqueda_twitter` — Live Twitter/X search via Apify MCP
- `busqueda_reddit` — Live Reddit search via Apify MCP

### 5. Mathematical Analysis Engine

1,650 lines of quantitative analysis (`core/math_engine.py`):

- **Exchange rates:** Dolar velocity, volatility, spreads (blue/MEP/CCL), crawling peg analysis, implicit rates
- **Interest rates:** Real rates (BADLAR vs inflation), carry trade returns (multi-currency), fixed-term deposit rankings
- **Monetary:** Base money expansion, deposit ratios, monetary multiplier, reserves burn rate
- **Activity:** EMAE (economic activity) trends, seasonally adjusted, purchasing power erosion
- **Risk:** Country risk (CDS) analysis, sentiment scoring from social media, news volume spikes
- **Composite:** **Nyx Index** — a 0-100 risk score combining all signals into a single actionable metric

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.14, FastAPI, Uvicorn |
| **AI** | Anthropic Claude (Haiku/Sonnet/Opus) via SDK |
| **MCP** | Model Context Protocol — Apify tools |
| **Database** | PostgreSQL with full-text search (Spanish), pg_trgm fuzzy matching |
| **Scraping** | Apify Cloud (web, Twitter/X, Reddit, news extraction) |
| **Transcription** | youtube-transcript-api, yt-dlp |
| **Frontend** | Vanilla JS + Leaflet maps + SSE streaming |
| **Design** | "Liquid Glass Dark" — glassmorphism with particle animations |
| **Data Sources** | BCRA API, Bluelytics, INDEC, RSS feeds, Google Trends |

---

## Quick Start

### Prerequisites

- Python 3.12+ (3.14 recommended)
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 15+ (optional — app works without it)
- Anthropic API key
- Apify API token

### 1. Clone & Configure

```bash
git clone https://github.com/matiasfrancia/nyx-terminal.git
cd nyx-terminal
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install & Run

**Windows (one click):**
```bash
start.bat
```

**Manual:**
```bash
uv venv .venv --python 3.14
uv pip install -r requirements.txt

# Start Diaricat Live (transcription service)
python diaricat_service.py &

# Start API + Frontend
uvicorn api:app --reload --port 8000
```

### 3. Open

- **Dashboard:** http://localhost:8000/map
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/

---

## API Reference

### Data Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/summary` | Full data status overview |
| GET | `/dolar` | Current rates (all 7 types) |
| GET | `/dolar/blue` | Blue dollar rate |
| GET | `/dolar/historial/{tipo}?dias=30` | Historical rates |
| GET | `/bcra/{variable}` | BCRA data (reservas, tasas, base_monetaria...) |
| GET | `/riesgo-pais` | Country risk (EMBI+) |
| GET | `/inflacion?meses=12` | Monthly inflation |
| GET | `/signals` | All derived signals |
| GET | `/eventos` | Classified events with urgency |
| GET | `/tweets` | Twitter/X data |
| GET | `/reddit` | Reddit posts |
| GET | `/trends` | Google Trends |

### Analysis Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analisis` | Complete analysis report |
| GET | `/analisis/indice-nyx` | Nyx Risk Index (0-100) |
| GET | `/analisis/resumen` | Executive summary |
| GET | `/analisis/dolar/velocidad` | Dolar rate of change |
| GET | `/analisis/dolar/spreads` | Blue/MEP/CCL spreads |
| GET | `/analisis/carry-trade` | Carry trade returns |
| GET | `/analisis/sentiment` | Social media sentiment |
| GET | `/analisis/monetario` | Monetary analysis (4 metrics) |

### AI Agent

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agent/ask` | Synchronous query `{"question": "..."}` |
| POST | `/agent/stream` | SSE streaming response |

### Live Monitoring

| Method | Path | Description |
|--------|------|-------------|
| POST | `/live/start` | Start YouTube transcription `{"url": "..."}` |
| GET | `/live/events/stream` | SSE event stream (transcript + alerts) |
| GET | `/live/keywords` | List alert keywords |
| POST | `/live/keywords` | Add keyword `{"keyword": "...", "sector": "...", "urgency": 5}` |
| DELETE | `/live/keywords/{keyword}` | Remove keyword |
| GET | `/live/status` | Active sessions |

### Configuration

| Method | Path | Description |
|--------|------|-------------|
| GET | `/config` | Current configuration |
| PUT | `/config` | Update settings |
| GET | `/config/options` | Valid options |

---

## Database Schema

PostgreSQL with full-text search in Spanish:

```sql
cotizaciones    — Exchange rates, indices (dolar_blue, dolar_mep, riesgo_pais...)
bcra_variables  — Central Bank data (reserves, rates, monetary base)
noticias        — News articles with TSVECTOR full-text index
tweets          — Twitter/X data
reddit_posts    — Reddit content
eventos         — Classified events (type, urgency, sector, affected assets)
agente_contexto — Agent-saved insights & memory
snapshots       — Historical analysis snapshots
trends          — Google Trends data
rendimientos    — Fixed-term rates + crypto yields
```

Setup:
```bash
# Create database and tables
python db/setup.py

# Seed initial data
python db/seed.py
```

---

## Project Structure

```
nyx-terminal/
├── api.py                   # FastAPI server (port 8000) — 40+ endpoints
├── main.py                  # CLI entry point
├── diaricat_service.py      # Live transcription service (port 8766)
├── nyx_diaricat_client.py   # Diaricat client library
├── start.bat                # Windows one-click launcher
├── requirements.txt         # Python dependencies
├── config.json              # Runtime configuration
├── .env.example             # Environment variable template
│
├── core/
│   ├── agent.py             # NyxAgent — Claude AI + tool use + budget guard
│   ├── mcp_apify.py         # MCP server — Apify actors as MCP tools
│   ├── math_engine.py       # 80+ quantitative analysis functions (1,650 LOC)
│   ├── signals.py           # Derived signals (brecha, tasa real, presion)
│   ├── classifier.py        # Event classification (5 types + urgency)
│   ├── store.py             # DataStore — loads/serves all cached data
│   ├── config.py            # Configuration management
│   ├── context_writer.py    # PostgreSQL context persistence
│   └── db.py                # Database connection pool & CRUD
│
├── db/
│   ├── schema.sql           # Full PostgreSQL schema with FTS indexes
│   ├── setup.py             # Database creation script
│   └── seed.py              # Initial data seeding
│
├── frontend/
│   ├── index.html           # Single-page app shell
│   ├── css/                 # Liquid Glass Dark theme
│   │   ├── nyx.css          # Core styles + glassmorphism
│   │   ├── nyx-map.css      # Map-specific styles
│   │   └── nyx-chat.css     # Chat panel styles
│   ├── js/
│   │   ├── nyx-app.js       # Main application (112KB) — dashboard, charts, KPIs
│   │   ├── nyx-map.js       # Interactive Argentina map (Leaflet + clusters)
│   │   ├── nyx-live.js      # Live alert streaming + transcript display
│   │   ├── nyx-drawer.js    # Sidebar navigation
│   │   └── nyx-particles.js # Background particle animations
│   └── data/                # GeoJSON + demo event data
│
├── data/
│   ├── nyx-apify-actors.json          # Apify actor definitions
│   ├── nyx-events-demo.json           # Sample events for map demo
│   ├── nyx-preload-data.json          # Preloaded data for offline mode
│   ├── provincias.geojson             # Argentine provinces boundaries
│   └── DIARICAT-LIVE-INTEGRATION.md   # Diaricat API documentation
│
└── scripts/
    ├── download_all_apis.py   # Fetch all economic APIs
    ├── download_all_apify.py  # Scrape via Apify actors
    ├── generate_pdf.py        # Export analysis as PDF
    └── consolidate_results.py # Merge all data sources
```

---

## How the MCP Integration Works

The Model Context Protocol (MCP) enables Claude to autonomously decide when to query external data sources:

```
User Question
     │
     ▼
┌─────────────┐    "Local data is stale"    ┌───────────────┐
│  NyxAgent   │ ─────────────────────────── │  MCP Server   │
│  (Claude)   │    Tool call: apify_*       │  (mcp_apify)  │
└──────┬──────┘                              └───────┬───────┘
       │                                             │
       │  "Budget: $0.12 / $0.50"                    │  Apify API
       │                                             ▼
       │                                    ┌────────────────┐
       │                                    │  Apify Cloud   │
       │                                    │  Web / Twitter  │
       │                                    │  Reddit / News  │
       │                                    └────────┬───────┘
       │                                             │
       ▼                                             ▼
┌─────────────┐                             Fresh results
│  Synthesize │ ◄───────────────────────────
│  Response   │
└─────────────┘
```

The agent always tries local data first (free, instant). MCP tools are only invoked when the agent determines it needs fresher or broader data — and always within budget constraints.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for the AI agent |
| `APIFY_TOKEN` | Yes | Apify token for live scraping |
| `DATABASE_URL` | No | PostgreSQL connection string (enables persistent context) |
| `DIARICAT_LIVE_URL` | No | Transcription service URL (default: `http://127.0.0.1:8766`) |

---

## License

MIT

---

## Team

Built with Claude AI (Anthropic) + Model Context Protocol for the MCP Hackathon 2025.
