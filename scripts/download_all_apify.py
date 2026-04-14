"""Nyx Terminal — Bajada masiva de Apify actors (Starter plan)"""
import json
import os
from datetime import datetime
from apify_client import ApifyClient

TOKEN = "apify_api_YOUR_TOKEN_HERE"
client = ApifyClient(TOKEN)
BASE = "info"

def save(path, data):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    size = os.path.getsize(full)
    print(f"  >> {full} ({size//1024}KB)")

def p(msg): print(msg)

# ═══════════════════════════════════════
# TWITTER — busquedas amplias
# ═══════════════════════════════════════
p("=== TWITTER (xtdata/twitter-x-scraper) ===")
twitter_queries = [
    ("bcra", ["BCRA"], 50),
    ("dolar_blue", ["dolar blue"], 50),
    ("inflacion", ["inflacion argentina"], 30),
    ("riesgo_pais", ["riesgo pais argentina"], 30),
    ("economia_ar", ["economia argentina"], 30),
    ("merval", ["merval bolsa argentina"], 30),
    ("cepo_cambiario", ["cepo cambiario"], 20),
    ("devaluacion", ["devaluacion peso argentino"], 20),
    ("paro_sindical", ["paro sindical argentina"], 20),
    ("inversiones_ar", ["inversiones argentina cedear"], 20),
    ("banco_central", ["@BancoCentral_AR"], 20),
    ("milei_economia", ["milei economia"], 20),
]

all_tweets = {}
for qname, terms, max_tw in twitter_queries:
    p(f"\n  >> {qname}: {terms}")
    try:
        run = client.actor("xtdata/twitter-x-scraper").call(
            run_input={"searchTerms": terms, "maxTweets": max_tw},
            timeout_secs=120
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"     OK: {len(items)} tweets")
        # Limpiar data relevante
        clean = []
        for it in items:
            clean.append({
                "id": it.get("id"),
                "text": it.get("full_text", it.get("text", "")),
                "author": it.get("author", {}).get("screen_name", it.get("author", "")) if isinstance(it.get("author"), dict) else it.get("author", ""),
                "created_at": it.get("created_at", ""),
                "likes": it.get("favorite_count", it.get("likeCount", 0)),
                "retweets": it.get("retweet_count", it.get("retweetCount", 0)),
                "replies": it.get("reply_count", it.get("replyCount", 0)),
                "url": it.get("url", it.get("twitterUrl", "")),
            })
        save(f"twitter/{qname}.json", clean)
        all_tweets[qname] = clean
        if clean:
            p(f"     Sample: @{clean[0].get('author','?')}: {clean[0].get('text','')[:80]}")
    except Exception as e:
        p(f"     X: {e}")
        all_tweets[qname] = {"error": str(e)[:200]}

save("twitter/_all_twitter.json", {"fetched_at": datetime.now().isoformat(), "queries": all_tweets})
total_tw = sum(len(v) for v in all_tweets.values() if isinstance(v, list))
p(f"\n  TOTAL TWEETS: {total_tw}")

# ═══════════════════════════════════════
# GOOGLE TRENDS — terminos economicos AR
# ═══════════════════════════════════════
p("\n=== GOOGLE TRENDS ===")
trends_batches = [
    ["dolar blue", "inflacion argentina", "riesgo pais", "BCRA", "devaluacion"],
    ["merval", "plazo fijo", "cedear", "bonos argentina", "cripto argentina"],
    ["paro camioneros", "corralito", "cepo cambiario", "FMI argentina", "reservas BCRA"],
]

all_trends = []
for batch in trends_batches:
    p(f"  >> Trends: {batch}")
    try:
        run = client.actor("apify/google-trends-scraper").call(
            run_input={"searchTerms": batch, "geo": "AR", "timeRange": "today 1-m"},
            timeout_secs=180
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"     OK: {len(items)} terminos")
        for it in items:
            term = it.get("searchTerm", it.get("inputUrlOrTerm", "?"))
            timeline = it.get("interestOverTime_timelineData", [])
            p(f"     {term}: {len(timeline)} data points")
            all_trends.append({
                "term": term,
                "timeline": timeline,
                "related_queries_top": it.get("relatedQueries_top", [])[:10],
                "related_queries_rising": it.get("relatedQueries_rising", [])[:10],
                "related_topics_top": it.get("relatedTopics_top", [])[:10],
                "interest_by_subregion": it.get("interestBySubregion", []),
            })
    except Exception as e:
        p(f"     X: {e}")

save("trends/google_trends_ar.json", {"fetched_at": datetime.now().isoformat(), "trends": all_trends})
p(f"  TOTAL TRENDS: {len(all_trends)} terminos")

# ═══════════════════════════════════════
# RAG WEB BROWSER — noticias y analisis
# ═══════════════════════════════════════
p("\n=== RAG WEB BROWSER ===")
rag_queries = [
    ("noticias_economia", "noticias economía argentina abril 2026", 10),
    ("bcra_resoluciones", "BCRA resolución comunicación tipo cambio abril 2026", 5),
    ("boletin_oficial", "site:boletinoficial.gob.ar decreto resolución abril 2026", 5),
    ("infobae_economia", "site:infobae.com economía argentina abril 2026", 8),
    ("paro_sindical", "paro sindical camioneros transporte argentina 2026", 5),
    ("cgt_medidas", "CGT comunicado medida de fuerza 2026", 3),
    ("inversiones_cedear", "mejores inversiones argentina 2026 cedear bonos plazo fijo", 5),
    ("tipo_cambio_analisis", "tipo de cambio real argentina atraso cambiario 2026", 5),
    ("fmi_argentina", "FMI acuerdo argentina 2026 desembolso", 5),
    ("energia_tarifas", "tarifas energia electricidad gas argentina 2026", 5),
    ("agro_exportaciones", "cosecha gruesa exportaciones argentina 2026 soja trigo", 5),
    ("mineria_litio", "litio mineria argentina inversiones 2026", 3),
    ("construccion_inmobiliario", "construccion inmobiliario creditos hipotecarios argentina 2026", 3),
    ("turismo_temporada", "turismo argentina temporada alta 2026 ingresos", 3),
    ("tecnologia_startups", "startups tecnologia argentina 2026 inversiones fintech", 3),
]

all_rag = {}
for qname, query, max_r in rag_queries:
    p(f"\n  >> {qname}: {query[:50]}...")
    try:
        run = client.actor("apify/rag-web-browser").call(
            run_input={"query": query, "maxResults": max_r},
            timeout_secs=120
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"     OK: {len(items)} resultados")
        clean = []
        for it in items:
            title = it.get("title", "")
            url = it.get("url", "")
            md = it.get("markdown", it.get("text", ""))
            p(f"     - {title[:60] if title else url[:60]}")
            clean.append({"title": title, "url": url, "markdown": md[:2000]})
        save(f"rag/{qname}.json", clean)
        all_rag[qname] = clean
    except Exception as e:
        p(f"     X: {e}")
        all_rag[qname] = {"error": str(e)[:200]}

save("rag/_all_rag.json", {"fetched_at": datetime.now().isoformat(), "queries": {k: len(v) if isinstance(v, list) else v for k, v in all_rag.items()}})

# ═══════════════════════════════════════
# REDDIT — r/merval y r/argentina
# ═══════════════════════════════════════
p("\n=== REDDIT ===")
subreddits = [
    ("merval_hot", "https://www.reddit.com/r/merval/hot/", 25),
    ("merval_new", "https://www.reddit.com/r/merval/new/", 25),
    ("argentina_economia", "https://www.reddit.com/r/argentina/search/?q=economia+dolar&sort=new", 15),
]
all_reddit = {}
for sname, surl, max_items in subreddits:
    p(f"\n  >> {sname}")
    try:
        run = client.actor("trudax/reddit-scraper-lite").call(
            run_input={"startUrls": [{"url": surl}], "maxItems": max_items},
            timeout_secs=90
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"     OK: {len(items)} posts")
        clean = []
        for it in items:
            clean.append({
                "title": it.get("title", it.get("postTitle", "")),
                "url": it.get("url", it.get("postUrl", "")),
                "body": str(it.get("body", it.get("postText", "")))[:500],
                "score": it.get("score", it.get("numberOfUpvotes", 0)),
                "comments": it.get("numberOfComments", it.get("numComments", 0)),
                "author": it.get("author", it.get("username", "")),
                "created": it.get("createdAt", it.get("created", "")),
            })
            if clean[-1]["title"]:
                p(f"     - {clean[-1]['title'][:60]}")
        save(f"reddit/{sname}.json", clean)
        all_reddit[sname] = clean
    except Exception as e:
        p(f"     X: {e}")
        all_reddit[sname] = {"error": str(e)[:200]}

save("reddit/_all_reddit.json", {"fetched_at": datetime.now().isoformat(), "subreddits": all_reddit})

# ═══════════════════════════════════════
# ARTICLE EXTRACTOR — medios sin RSS
# ═══════════════════════════════════════
p("\n=== ARTICLE EXTRACTOR ===")
sites = [
    ("infobae_economia", "https://www.infobae.com/economia/", 15),
    ("pagina12_economia", "https://www.pagina12.com.ar/secciones/economia", 10),
    ("lanacion_economia", "https://www.lanacion.com.ar/economia/", 10),
    ("ambito_finanzas", "https://www.ambito.com/finanzas", 10),
    ("iprofesional_finanzas", "https://www.iprofesional.com/finanzas", 10),
]
all_articles = {}
for sname, surl, max_items in sites:
    p(f"\n  >> {sname}: {surl}")
    try:
        run = client.actor("lukaskrivka/article-extractor-smart").call(
            run_input={
                "startUrls": [{"url": surl}],
                "onlyNewArticles": False,
                "crawlWholeSubdomain": False,
                "maxItems": max_items,
            },
            timeout_secs=120
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"     OK: {len(items)} articulos")
        clean = []
        for it in items:
            clean.append({
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "date": it.get("date", ""),
                "author": it.get("author", ""),
                "text": it.get("text", "")[:1000],
                "description": it.get("description", ""),
            })
            if clean[-1]["title"]:
                p(f"     - {clean[-1]['title'][:60]}")
        save(f"articles/{sname}.json", clean)
        all_articles[sname] = clean
    except Exception as e:
        p(f"     X: {e}")
        all_articles[sname] = {"error": str(e)[:200]}

save("articles/_all_articles.json", {"fetched_at": datetime.now().isoformat(), "sites": {k: len(v) if isinstance(v, list) else v for k, v in all_articles.items()}})

# ═══════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════
p("\n" + "="*60)
p("APIFY BAJADA COMPLETA")
p("="*60)
total_tw2 = sum(len(v) for v in all_tweets.values() if isinstance(v, list))
total_rag2 = sum(len(v) for v in all_rag.values() if isinstance(v, list))
total_reddit2 = sum(len(v) for v in all_reddit.values() if isinstance(v, list))
total_articles2 = sum(len(v) for v in all_articles.values() if isinstance(v, list))
p(f"  Tweets: {total_tw2}")
p(f"  Trends: {len(all_trends)} terminos")
p(f"  RAG results: {total_rag2}")
p(f"  Reddit posts: {total_reddit2}")
p(f"  Articles: {total_articles2}")

total_size = 0
for root, dirs, files in os.walk(BASE):
    for f in files:
        total_size += os.path.getsize(os.path.join(root, f))
p(f"  Total info/: {total_size//1024} KB")
