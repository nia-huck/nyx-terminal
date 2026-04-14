"""Nyx Terminal — FastAPI server.

Expone toda la data y senales via REST API.
    uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from pydantic import BaseModel

from core.store import DataStore
from core.signals import all_signals, brecha_cambiaria, tasa_real, tendencia_reservas, presion_cambiaria
from core.classifier import classify_all
from core import math_engine

app = FastAPI(title="Nyx Terminal API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

store = DataStore()

# ── Health ────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "name": "Nyx Terminal", "version": "1.0.0"}

@app.get("/summary")
def summary():
    return store.summary()

# ── Dolar ─────────────────────────────────────────

@app.get("/dolar")
def dolar():
    return store.dolar_actual()

@app.get("/dolar/blue")
def dolar_blue():
    return store.dolar_blue()

@app.get("/dolar/historial/{tipo}")
def dolar_historial(tipo: str = "blue", dias: int = 30):
    return store.dolar_historial(tipo, dias)

# ── BCRA ──────────────────────────────────────────

@app.get("/bcra/{variable}")
def bcra(variable: str):
    return store.bcra_variable(variable)

@app.get("/reservas")
def reservas():
    return store.reservas()

# ── Riesgo pais ───────────────────────────────────

@app.get("/riesgo-pais")
def riesgo_pais():
    return store.riesgo_pais()

@app.get("/riesgo-pais/historial")
def riesgo_pais_hist(dias: int = 30):
    return store.riesgo_pais_historial(dias)

# ── Inflacion ─────────────────────────────────────

@app.get("/inflacion")
def inflacion(meses: int = 12):
    return store.inflacion_mensual(meses)

# ── Senales derivadas ─────────────────────────────

@app.get("/signals")
def signals():
    return all_signals(store)

@app.get("/signals/brecha")
def sig_brecha():
    return brecha_cambiaria(store)

@app.get("/signals/tasa-real")
def sig_tasa_real():
    return tasa_real(store)

@app.get("/signals/reservas")
def sig_reservas():
    return tendencia_reservas(store)

@app.get("/signals/presion")
def sig_presion():
    return presion_cambiaria(store)

# ── Noticias y eventos ────────────────────────────

@app.get("/noticias")
def noticias(fuente: str | None = None):
    return store.noticias(fuente)

@app.get("/eventos")
def eventos():
    noticias = store.noticias()
    return classify_all(noticias)

# ── Social ────────────────────────────────────────

@app.get("/tweets")
def tweets(query: str | None = None):
    return store.tweets(query)

@app.get("/reddit")
def reddit(sub: str | None = None):
    return store.reddit(sub)

@app.get("/trends")
def trends():
    return store.trends()


# ── Analisis matematico ──────────────────────────

@app.get("/analisis")
def analisis_completo():
    return math_engine.reporte_completo(store)

@app.get("/analisis/indice-nyx")
def analisis_indice():
    return math_engine.indice_nyx(store)

@app.get("/analisis/resumen")
def analisis_resumen():
    return {"texto": math_engine.resumen_ejecutivo(store)}

@app.get("/analisis/dolar/velocidad")
def analisis_dolar_velocidad():
    return math_engine.dolar_velocidad(store)

@app.get("/analisis/dolar/spreads")
def analisis_dolar_spreads():
    return math_engine.dolar_spreads(store)

@app.get("/analisis/dolar/implicito")
def analisis_dolar_implicito():
    return math_engine.dolar_implicito(store)

@app.get("/analisis/dolar/crawling-peg")
def analisis_crawling_peg():
    return math_engine.crawling_peg(store)

@app.get("/analisis/inflacion")
def analisis_inflacion():
    return math_engine.inflacion_analisis(store)

@app.get("/analisis/actividad")
def analisis_actividad():
    return math_engine.actividad_emae(store)

@app.get("/analisis/tasas")
def analisis_tasas():
    return math_engine.tasas_reales(store)

@app.get("/analisis/carry-trade")
def analisis_carry():
    return math_engine.carry_trade(store)

@app.get("/analisis/plazo-fijo")
def analisis_plazo_fijo():
    return math_engine.ranking_plazo_fijo(store)

@app.get("/analisis/crypto")
def analisis_crypto():
    return math_engine.ranking_crypto_yields(store)

@app.get("/analisis/riesgo-pais")
def analisis_riesgo():
    return math_engine.riesgo_pais_analisis(store)

@app.get("/analisis/reservas")
def analisis_reservas():
    return math_engine.reservas_velocidad(store)

@app.get("/analisis/monetario")
def analisis_monetario():
    return {
        "expansion": math_engine.expansion_monetaria(store),
        "depositos_ratio": math_engine.depositos_ratio(store),
        "depositos_tendencia": math_engine.depositos_tendencia(store),
        "multiplicador": math_engine.multiplicador_monetario(store),
    }

@app.get("/analisis/poder-adquisitivo")
def analisis_poder():
    return math_engine.poder_adquisitivo(store)

@app.get("/analisis/dolar/euro")
def analisis_dolar_euro():
    return math_engine.dolar_euro(store)

@app.get("/analisis/inflacion/core-vs-headline")
def analisis_core_headline():
    return math_engine.inflacion_core_vs_headline(store)

@app.get("/analisis/inflacion/extendida")
def analisis_inflacion_ext():
    return math_engine.inflacion_extendida(store)

@app.get("/analisis/actividad/ajustada")
def analisis_actividad_adj():
    return math_engine.actividad_emae_ajustada(store)

@app.get("/analisis/tasa-politica")
def analisis_tasa_pol():
    return math_engine.tasa_politica(store)

@app.get("/analisis/carry-trade/multi")
def analisis_carry_multi():
    return math_engine.carry_trade_multi(store)

@app.get("/analisis/multiplicador")
def analisis_mult():
    return math_engine.multiplicador_monetario(store)

@app.get("/analisis/depositos/tendencia")
def analisis_dep_tend():
    return math_engine.depositos_tendencia(store)

@app.get("/analisis/sentiment")
def analisis_sentiment():
    return math_engine.sentiment_social(store)

@app.get("/analisis/noticias-volumen")
def analisis_not_vol():
    return math_engine.noticias_volumen(store)


# ── Configuracion ────────────────────────────────

from core.config import get_config, update_config, get_config_schema, VALID_OPTIONS, GROUPS

@app.get("/config")
def config_get():
    return get_config_schema()

@app.put("/config")
async def config_update(request: Request):
    body = await request.json()
    return update_config(body)

@app.get("/config/options")
def config_options():
    return {"options": VALID_OPTIONS, "groups": GROUPS}


# ── Agente IA ─────────────────────────────────────

class AgentQuery(BaseModel):
    question: str
    max_budget: float | None = None
    verbose: bool = False

@app.post("/agent/ask")
async def agent_ask(q: AgentQuery):
    import asyncio
    from core.agent import NyxAgent

    overrides = {}
    if q.max_budget is not None:
        overrides["max_budget_per_query"] = q.max_budget

    try:
        agent = NyxAgent.from_config(**overrides)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando agente: {str(e)[:200]}")

    if not agent.client:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY no configurado")

    result = await asyncio.to_thread(agent.ask, q.question, q.verbose)
    return result


@app.post("/agent/stream")
async def agent_stream(q: AgentQuery):
    """SSE streaming — el frontend recibe eventos en tiempo real."""
    import asyncio, queue, threading
    from core.agent import NyxAgent

    overrides = {}
    if q.max_budget is not None:
        overrides["max_budget_per_query"] = q.max_budget

    try:
        agent = NyxAgent.from_config(**overrides)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

    event_queue: queue.Queue = queue.Queue()

    def _run():
        try:
            for event in agent.ask_stream(q.question):
                event_queue.put(event)
        except Exception as e:
            event_queue.put({"type": "error", "data": str(e)[:300]})
        finally:
            event_queue.put(None)  # sentinel

    threading.Thread(target=_run, daemon=True).start()

    async def _generate():
        import json as _json
        while True:
            # Poll queue without blocking the event loop
            try:
                event = await asyncio.to_thread(event_queue.get, timeout=120)
            except Exception:
                break
            if event is None:
                break
            yield f"data: {_json.dumps(event, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


# ── Live Monitor (Diaricat Live proxy) ───────────

import httpx as _httpx

DIARICAT_BASE = os.getenv("DIARICAT_URL", "http://127.0.0.1:8766")


class LiveStartRequest(BaseModel):
    url: str
    language: str = "es"


@app.post("/live/start")
async def live_start(req: LiveStartRequest):
    """Start a new Diaricat Live stream session."""
    try:
        async with _httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{DIARICAT_BASE}/v1/stream/start",
                json={"url": req.url, "language": req.language},
            )
            resp.raise_for_status()
            return resp.json()
    except _httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Servicio Diaricat no disponible (puerto 8766 sin respuesta)")
    except _httpx.HTTPStatusError as exc:
        body = exc.response.text[:200]
        raise HTTPException(status_code=exc.response.status_code, detail=body or f"HTTP {exc.response.status_code}")
    except _httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.delete("/live/stop/{session_id}")
async def live_stop(session_id: str):
    """Stop a Diaricat Live stream session."""
    try:
        async with _httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{DIARICAT_BASE}/v1/stream/stop/{session_id}",
            )
            resp.raise_for_status()
            return resp.json()
    except _httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/live/status")
async def live_status():
    """List active Diaricat Live sessions."""
    try:
        async with _httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{DIARICAT_BASE}/v1/stream/status")
            resp.raise_for_status()
            return resp.json()
    except _httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/live/events/stream")
async def live_events_stream(session_id: str | None = None):
    """SSE proxy: re-emits Diaricat Live events (transcript + alerts) to the frontend."""
    import asyncio
    import json as _json

    sse_url = (
        f"{DIARICAT_BASE}/v1/stream/events/{session_id}"
        if session_id
        else f"{DIARICAT_BASE}/v1/stream/events"
    )

    async def _generate():
        try:
            async with _httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", sse_url) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        try:
                            detail = _json.loads(body).get("detail", f"HTTP {response.status_code}")
                        except Exception:
                            detail = f"HTTP {response.status_code}"
                        yield f"event: error\ndata: {_json.dumps({'message': detail})}\n\n"
                        return
                    async for line in response.aiter_lines():
                        yield line + "\n"
        except _httpx.ConnectError:
            yield f"event: error\ndata: {_json.dumps({'message': 'Servicio Diaricat no disponible'})}\n\n"
        except _httpx.ReadError:
            pass
        except Exception as exc:
            yield f"event: error\ndata: {_json.dumps({'message': str(exc)})}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Live Keywords proxy ──────────────────────────

class KeywordAddRequest(BaseModel):
    keyword: str
    sector: str = "general"
    urgency: int = 5

@app.get("/live/keywords")
async def live_keywords():
    try:
        async with _httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{DIARICAT_BASE}/v1/keywords")
            resp.raise_for_status()
            return resp.json()
    except _httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Servicio Diaricat no disponible")
    except _httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

@app.post("/live/keywords")
async def live_keywords_add(body: KeywordAddRequest):
    try:
        async with _httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(f"{DIARICAT_BASE}/v1/keywords", json=body.model_dump())
            resp.raise_for_status()
            return resp.json()
    except _httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Servicio Diaricat no disponible")
    except _httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

@app.delete("/live/keywords/{keyword}")
async def live_keywords_remove(keyword: str):
    try:
        async with _httpx.AsyncClient(timeout=5) as client:
            resp = await client.delete(f"{DIARICAT_BASE}/v1/keywords/{keyword}")
            resp.raise_for_status()
            return resp.json()
    except _httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Servicio Diaricat no disponible")
    except _httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


# ── Frontend (mapa interactivo) ──────────────────

_frontend = Path(__file__).parent / "frontend"

app.mount("/css", StaticFiles(directory=_frontend / "css"), name="css")
app.mount("/js", StaticFiles(directory=_frontend / "js"), name="js")
app.mount("/data", StaticFiles(directory=_frontend / "data"), name="frontend-data")

def _html_response():
    content = (_frontend / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=content, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    })

@app.get("/map")
def map_page():
    return _html_response()

@app.get("/app")
def app_page():
    return _html_response()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
