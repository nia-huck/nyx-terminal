"""Nyx Terminal - Bloque 3: Test de Apify Actors"""
import json
import time
from apify_client import ApifyClient

TOKEN = "apify_api_YOUR_TOKEN_HERE"
client = ApifyClient(TOKEN)
store = client.store()
ALL_RESULTS = {}

def p(msg): print(msg)

# ── 3a. BUSCAR ACTORS ──
p("\n=== 3a. BUSCAR ACTORS EN STORE ===")
searches = {
    "twitter scraper": 3,
    "google news scraper": 3,
    "reddit scraper": 3,
    "google trends scraper": 3,
    "article extractor": 3,
}
for query, limit in searches.items():
    p(f"\n  >> '{query}':")
    try:
        actors = list(store.list(search=query, limit=limit).items)
        for a in actors:
            name = f"{a.get('username','?')}/{a.get('name','?')}"
            runs = a.get("stats", {}).get("totalRuns", "?")
            users = a.get("stats", {}).get("totalUsers", a.get("stats", {}).get("totalUsers30Days", "?"))
            p(f"     {name} | runs={runs} | users={users}")
        ALL_RESULTS[f"store_{query.replace(' ','_')}"] = {
            "status": "OK",
            "actors": [{"id": f"{a.get('username')}/{a.get('name')}", "runs": a.get("stats",{}).get("totalRuns"), "users": a.get("stats",{}).get("totalUsers")} for a in actors]
        }
    except Exception as e:
        p(f"     X Error: {e}")
        ALL_RESULTS[f"store_{query.replace(' ','_')}"] = {"status": "FAIL", "error": str(e)}

# ── 3b. RAG WEB BROWSER ──
p("\n=== 3b. RAG WEB BROWSER ===")
rag_queries = [
    ("BCRA tipo cambio", {"query": "BCRA resolucion tipo de cambio Argentina abril 2026", "maxResults": 3}),
    ("Paro camioneros", {"query": "paro camioneros Argentina 2026", "maxResults": 3}),
    ("Boletin Oficial", {"query": "site:boletinoficial.gob.ar decreto abril 2026", "maxResults": 3}),
]
for qname, qinput in rag_queries:
    p(f"\n  >> Query: {qname}")
    try:
        run = client.actor("apify/rag-web-browser").call(run_input=qinput, timeout_secs=90)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"     OK: {len(items)} resultados")
        for i, item in enumerate(items):
            title = item.get("title", item.get("metadata", {}).get("title", "?"))
            url = item.get("url", item.get("metadata", {}).get("url", "?"))
            text = str(item.get("markdown", item.get("text", "")))[:120]
            p(f"     [{i+1}] {title[:80]}")
            p(f"         URL: {url}")
            p(f"         Preview: {text}...")
        ALL_RESULTS[f"rag_{qname.replace(' ','_')}"] = {
            "status": "OK",
            "count": len(items),
            "results": [{"title": it.get("title","?"), "url": it.get("url","?"), "text_preview": str(it.get("markdown",it.get("text","")))[:200]} for it in items]
        }
    except Exception as e:
        p(f"     X Error: {e}")
        ALL_RESULTS[f"rag_{qname.replace(' ','_')}"] = {"status": "FAIL", "error": str(e)}

# ── 3c. GOOGLE NEWS SCRAPER ──
p("\n=== 3c. GOOGLE NEWS SCRAPER ===")
try:
    # Find best google news actor
    news_actors = list(store.list(search="google news scraper", limit=3).items)
    best = f"{news_actors[0]['username']}/{news_actors[0]['name']}" if news_actors else None
    p(f"  Usando actor: {best}")
    if best:
        # Try to get the actor input schema first
        actor_info = client.actor(best).get()
        p(f"  Actor found: {actor_info.get('name', '?')}")

        # Common input patterns for google news scrapers
        news_input = {"query": "economia argentina", "maxItems": 5, "language": "es", "country": "AR"}
        p(f"  Running with input: {news_input}")
        run = client.actor(best).call(run_input=news_input, timeout_secs=90)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"  OK: {len(items)} noticias")
        for i, item in enumerate(items[:5]):
            title = item.get("title", item.get("headline", "?"))
            source = item.get("source", item.get("publisher", "?"))
            pub_date = item.get("publishedAt", item.get("date", item.get("published", "?")))
            url = item.get("url", item.get("link", "?"))
            p(f"     [{i+1}] {str(title)[:80]}")
            p(f"         Fuente: {source} | Fecha: {pub_date}")
            p(f"         URL: {url}")
        ALL_RESULTS["google_news_scraper"] = {
            "status": "OK", "actor": best, "count": len(items),
            "results": [{"title": it.get("title",it.get("headline","?")), "source": it.get("source","?"),
                         "date": str(it.get("publishedAt",it.get("date","?"))), "url": it.get("url","?")} for it in items[:5]]
        }
except Exception as e:
    p(f"  X Error: {e}")
    ALL_RESULTS["google_news_scraper"] = {"status": "FAIL", "error": str(e), "actor": best if 'best' in dir() else "?"}

# ── 3d. TWITTER/X SCRAPER ──
p("\n=== 3d. TWITTER/X SCRAPER ===")
try:
    tw_actors = list(store.list(search="twitter scraper", limit=3).items)
    best_tw = f"{tw_actors[0]['username']}/{tw_actors[0]['name']}" if tw_actors else None
    p(f"  Usando actor: {best_tw}")
    if best_tw:
        # Get input schema to understand expected format
        actor_info = client.actor(best_tw).get()
        # Try common input format
        tw_input = {"searchTerms": ["BCRA", "dolar blue"], "maxTweets": 10, "addUserInfo": False}
        p(f"  Running with: searchTerms=['BCRA', 'dolar blue'], maxTweets=10")
        try:
            run = client.actor(best_tw).call(run_input=tw_input, timeout_secs=90)
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            p(f"  OK: {len(items)} tweets")
            for i, item in enumerate(items[:5]):
                text = str(item.get("text", item.get("full_text", item.get("tweet_text", "?"))))[:100]
                author = item.get("author", item.get("user", {}).get("screen_name", item.get("username", "?")))
                p(f"     [{i+1}] @{author}: {text}")
            ALL_RESULTS["twitter_scraper"] = {
                "status": "OK", "actor": best_tw, "count": len(items),
                "tweets": [{"text": str(it.get("text",it.get("full_text","?")))[:200], "author": str(it.get("author",it.get("username","?")))} for it in items[:10]]
            }
        except Exception as e:
            p(f"  X Run failed: {e}")
            # Try to get the expected input schema
            p(f"  Intentando obtener input schema...")
            try:
                build_info = actor_info.get("defaultRunOptions", {})
                p(f"  Default run options: {build_info}")
            except:
                pass
            ALL_RESULTS["twitter_scraper"] = {"status": "FAIL", "actor": best_tw, "error": str(e)}
except Exception as e:
    p(f"  X Error general: {e}")
    ALL_RESULTS["twitter_scraper"] = {"status": "FAIL", "error": str(e)}

# ── 3e. REDDIT SCRAPER ──
p("\n=== 3e. REDDIT SCRAPER ===")
try:
    rd_actors = list(store.list(search="reddit scraper", limit=3).items)
    best_rd = f"{rd_actors[0]['username']}/{rd_actors[0]['name']}" if rd_actors else None
    p(f"  Usando actor: {best_rd}")
    if best_rd:
        rd_input = {"startUrls": [{"url": "https://www.reddit.com/r/merval/hot/"}], "maxItems": 5}
        p(f"  Running with r/merval, maxItems=5")
        run = client.actor(best_rd).call(run_input=rd_input, timeout_secs=90)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"  OK: {len(items)} posts")
        for i, item in enumerate(items[:5]):
            title = item.get("title", item.get("postTitle", "?"))
            score = item.get("score", item.get("upvotes", item.get("numberOfUpvotes", "?")))
            comments = item.get("numberOfComments", item.get("numComments", item.get("comments", "?")))
            p(f"     [{i+1}] {str(title)[:80]} | score={score} | comments={comments}")
        ALL_RESULTS["reddit_scraper"] = {
            "status": "OK", "actor": best_rd, "count": len(items),
            "posts": [{"title": it.get("title",it.get("postTitle","?")), "score": it.get("score","?"),
                        "comments": it.get("numberOfComments",it.get("numComments","?"))} for it in items[:5]]
        }
except Exception as e:
    p(f"  X Error: {e}")
    ALL_RESULTS["reddit_scraper"] = {"status": "FAIL", "error": str(e), "actor": best_rd if 'best_rd' in dir() else "?"}

# ── 3f. GOOGLE TRENDS SCRAPER ──
p("\n=== 3f. GOOGLE TRENDS SCRAPER ===")
try:
    p("  Usando actor: apify/google-trends-scraper")
    gt_input = {
        "searchTerms": ["dolar blue", "inflacion argentina", "paro"],
        "geo": "AR",
    }
    run = client.actor("apify/google-trends-scraper").call(run_input=gt_input, timeout_secs=120)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    p(f"  OK: {len(items)} resultados")
    for i, item in enumerate(items[:10]):
        term = item.get("searchTerm", item.get("term", "?"))
        values = item.get("interestOverTime", item.get("timelineData", []))
        if isinstance(values, list) and values:
            last_vals = values[-3:] if len(values) >= 3 else values
            p(f"     {term}: ultimos valores = {[v.get('value', v.get('values', v)) for v in last_vals]}")
        else:
            p(f"     {term}: {str(item)[:150]}")
    ALL_RESULTS["google_trends"] = {
        "status": "OK", "count": len(items),
        "results": [{"term": it.get("searchTerm","?"), "data_points": len(it.get("interestOverTime",it.get("timelineData",[])))} for it in items[:5]]
    }
except Exception as e:
    p(f"  X Error: {e}")
    ALL_RESULTS["google_trends"] = {"status": "FAIL", "error": str(e)}

# Save
with open("test_bloque3_results.json", "w", encoding="utf-8") as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False, default=str)
p("\n>> Guardado en test_bloque3_results.json")
