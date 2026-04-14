"""Nyx Terminal - Bajada completa de Apify actors"""
import json
import time
from apify_client import ApifyClient

TOKEN = "apify_api_YOUR_TOKEN_HERE"
client = ApifyClient(TOKEN)
store = client.store()
DATA = {}

def p(msg): print(msg)

# ═══════════════════════════════════════
# PARTE 1a: Buscar actors de Twitter GRATIS
# ═══════════════════════════════════════
p("=== BUSCAR ACTORS TWITTER ===")
tw_searches = ["twitter", "tweet scraper", "x.com scraper", "twitter search", "tweets"]
tw_all = {}
for q in tw_searches:
    try:
        actors = list(store.list(search=q, limit=10).items)
        for a in actors:
            aid = f"{a.get('username','?')}/{a.get('name','?')}"
            if aid not in tw_all:
                tw_all[aid] = {
                    "id": aid,
                    "title": a.get("title", "?"),
                    "users": a.get("stats", {}).get("totalUsers", 0),
                    "runs": a.get("stats", {}).get("totalRuns", 0),
                    "is_free": a.get("stats", {}).get("totalUsers", 0) > 0,  # can't determine from list
                    "found_via": q,
                }
    except Exception as e:
        p(f"  X search '{q}': {e}")

# Sort by users
tw_sorted = sorted(tw_all.values(), key=lambda x: x.get("users", 0), reverse=True)
p(f"  Found {len(tw_sorted)} unique Twitter actors:")
for a in tw_sorted[:15]:
    p(f"    {a['id']} | users={a['users']} | runs={a['runs']}")
DATA["twitter_actors_found"] = tw_sorted[:15]

# Try to run free ones (smaller/newer actors more likely to be free)
# Skip apidojo/tweet-scraper (known paid)
tw_to_try = [a for a in tw_sorted if "apidojo" not in a["id"] and a["users"] < 50000][:5]
tw_to_try += [a for a in tw_sorted if "free" in a["id"].lower() or "lite" in a["id"].lower()]

tested_tw = []
for a in tw_to_try[:6]:
    aid = a["id"]
    p(f"\n  Probando {aid}...")
    try:
        # Try common input patterns
        inputs_to_try = [
            {"searchTerms": ["BCRA"], "maxTweets": 5},
            {"searchQueries": ["BCRA"], "maxTweets": 5},
            {"queries": ["BCRA"], "maxItems": 5},
            {"query": "BCRA", "maxResults": 5},
            {"handles": ["BancoCentral_AR"], "maxTweets": 5},
        ]
        success = False
        for inp in inputs_to_try:
            try:
                run = client.actor(aid).call(run_input=inp, timeout_secs=60)
                items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
                if items and not items[0].get("noResults"):
                    p(f"    OK! {len(items)} results with input {list(inp.keys())}")
                    p(f"    Keys: {list(items[0].keys())[:10]}")
                    sample = str(items[0])[:200]
                    p(f"    Sample: {sample}")
                    tested_tw.append({"id": aid, "works": True, "input": inp, "count": len(items), "sample_keys": list(items[0].keys())[:15]})
                    success = True
                    break
                else:
                    p(f"    -- {list(inp.keys())}: empty/noResults")
            except Exception as e:
                err_str = str(e)
                if "paid" in err_str.lower() or "upgrade" in err_str.lower() or "free" in err_str.lower():
                    p(f"    X PAID: {err_str[:100]}")
                    tested_tw.append({"id": aid, "works": False, "reason": "paid_required"})
                    success = True  # stop trying
                    break
                # Try next input format
                continue
        if not success:
            tested_tw.append({"id": aid, "works": False, "reason": "no_compatible_input"})
            p(f"    X No compatible input found")
    except Exception as e:
        p(f"    X Error: {e}")
        tested_tw.append({"id": aid, "works": False, "reason": str(e)[:100]})

DATA["twitter_actors_tested"] = tested_tw

# ═══════════════════════════════════════
# PARTE 1b: Buscar actors de News GRATIS
# ═══════════════════════════════════════
p("\n\n=== BUSCAR ACTORS NEWS ===")
news_searches = ["google news", "news scraper", "article scraper", "news extractor"]
news_all = {}
for q in news_searches:
    try:
        actors = list(store.list(search=q, limit=10).items)
        for a in actors:
            aid = f"{a.get('username','?')}/{a.get('name','?')}"
            if aid not in news_all:
                news_all[aid] = {
                    "id": aid,
                    "title": a.get("title", "?"),
                    "users": a.get("stats", {}).get("totalUsers", 0),
                    "runs": a.get("stats", {}).get("totalRuns", 0),
                    "found_via": q,
                }
    except:
        pass

news_sorted = sorted(news_all.values(), key=lambda x: x.get("users", 0), reverse=True)
p(f"  Found {len(news_sorted)} unique News actors:")
for a in news_sorted[:10]:
    p(f"    {a['id']} | users={a['users']} | runs={a['runs']}")
DATA["news_actors_found"] = news_sorted[:10]

# Try article-extractor-smart (known good)
p("\n  Probando lukaskrivka/article-extractor-smart...")
try:
    run = client.actor("lukaskrivka/article-extractor-smart").call(
        run_input={"startUrls": [{"url": "https://www.ambito.com/economia"}], "onlyNewArticles": False, "crawlWholeSubdomain": False, "maxItems": 5},
        timeout_secs=90
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    p(f"    OK: {len(items)} articles")
    for it in items[:3]:
        p(f"    - {it.get('title','?')[:70]}")
    DATA["article_extractor_test"] = {"works": True, "count": len(items), "sample": [{"title": it.get("title","?"), "url": it.get("url","?"), "date": it.get("date","?")} for it in items[:5]]}
except Exception as e:
    p(f"    X: {e}")
    DATA["article_extractor_test"] = {"works": False, "error": str(e)[:200]}

# ═══════════════════════════════════════
# PARTE 1c: RAG Web Browser — bajada masiva
# ═══════════════════════════════════════
p("\n\n=== RAG WEB BROWSER (bajada masiva) ===")
rag_queries = [
    ("twitter_bcra", {"query": "site:x.com BCRA tipo de cambio 2026", "maxResults": 5}),
    ("twitter_banco_central", {"query": "site:x.com/BancoCentral_AR", "maxResults": 5}),
    ("google_news_ar", {"query": "economía argentina noticias hoy abril 2026", "maxResults": 10}),
    ("bcra_resoluciones", {"query": "BCRA resolución comunicación abril 2026", "maxResults": 5}),
    ("paro_camioneros", {"query": "paro camioneros argentina 2026", "maxResults": 5}),
    ("boletin_oficial", {"query": "site:boletinoficial.gob.ar decreto resolución 2026", "maxResults": 5}),
    ("infobae_economia", {"query": "site:infobae.com economía argentina abril 2026", "maxResults": 5}),
    ("sindicatos_cgt", {"query": "CGT comunicado paro 2026 argentina", "maxResults": 3}),
    ("sindicatos_camioneros", {"query": "camioneros medida de fuerza 2026", "maxResults": 3}),
]

DATA["rag_results"] = {}
for qname, qinput in rag_queries:
    p(f"\n  >> {qname}: {qinput['query'][:60]}...")
    try:
        run = client.actor("apify/rag-web-browser").call(run_input=qinput, timeout_secs=120)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"     OK: {len(items)} resultados")
        results = []
        for i, it in enumerate(items):
            title = it.get("title", "?")
            url = it.get("url", "?")
            text = str(it.get("markdown", it.get("text", "")))[:500]
            p(f"     [{i+1}] {title[:70]}")
            p(f"         {url}")
            results.append({"title": title, "url": url, "text": text})
        DATA["rag_results"][qname] = {"status": "OK", "count": len(items), "results": results}
    except Exception as e:
        p(f"     X: {e}")
        DATA["rag_results"][qname] = {"status": "FAIL", "error": str(e)[:200]}

# ═══════════════════════════════════════
# PARTE 1d: Google Trends
# ═══════════════════════════════════════
p("\n\n=== GOOGLE TRENDS ===")
try:
    run = client.actor("apify/google-trends-scraper").call(
        run_input={
            "searchTerms": ["dólar blue", "inflación", "paro", "devaluación", "riesgo país", "corralito", "BCRA"],
            "geo": "AR",
            "timeRange": "now 7-d",
        },
        timeout_secs=180
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    p(f"  OK: {len(items)} terminos")
    trends_data = []
    for it in items:
        term = it.get("searchTerm", it.get("inputUrlOrTerm", "?"))
        timeline = it.get("interestOverTime_timelineData", [])
        related_q = it.get("relatedQueries_top", [])
        p(f"  {term}: {len(timeline)} data points, {len(related_q)} related queries")
        trends_data.append({
            "term": term,
            "timeline": timeline[-10:] if timeline else [],
            "related_queries_top": related_q[:5] if related_q else [],
            "related_queries_rising": it.get("relatedQueries_rising", [])[:5],
        })
    DATA["google_trends"] = {"status": "OK", "terms": trends_data}
except Exception as e:
    p(f"  X: {e}")
    DATA["google_trends"] = {"status": "FAIL", "error": str(e)[:200]}

# ═══════════════════════════════════════
# PARTE 1e: Reddit
# ═══════════════════════════════════════
p("\n\n=== REDDIT ===")
try:
    run = client.actor("trudax/reddit-scraper-lite").call(
        run_input={"startUrls": [{"url": "https://www.reddit.com/r/merval/hot/"}], "maxItems": 20},
        timeout_secs=90
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    p(f"  OK: {len(items)} posts")
    reddit_data = []
    for it in items[:20]:
        title = it.get("title", it.get("postTitle", "?"))
        p(f"    - {str(title)[:70]}")
        reddit_data.append({
            "title": title,
            "url": it.get("url", it.get("postUrl", "?")),
            "score": it.get("score", it.get("numberOfUpvotes", "?")),
            "comments": it.get("numberOfComments", it.get("numComments", "?")),
            "body": str(it.get("body", it.get("postText", "")))[:300],
        })
    DATA["reddit_merval"] = {"status": "OK", "count": len(items), "posts": reddit_data}
except Exception as e:
    p(f"  X reddit actor: {e}")
    # Fallback to RAG
    p("  Trying RAG fallback...")
    try:
        run = client.actor("apify/rag-web-browser").call(
            run_input={"query": "site:reddit.com/r/merval dólar bonos 2026", "maxResults": 10},
            timeout_secs=90
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        p(f"  RAG fallback OK: {len(items)} results")
        DATA["reddit_merval"] = {"status": "OK_VIA_RAG", "count": len(items),
            "posts": [{"title": it.get("title","?"), "url": it.get("url","?"), "text": str(it.get("markdown",""))[:300]} for it in items]}
    except Exception as e2:
        DATA["reddit_merval"] = {"status": "FAIL", "error": str(e2)[:200]}

# ═══════════════════════════════════════
# PARTE 1f: Website Content Crawler
# ═══════════════════════════════════════
p("\n\n=== WEBSITE CONTENT CRAWLER ===")
try:
    run = client.actor("apify/website-content-crawler").call(
        run_input={"startUrls": [{"url": "https://www.ambito.com/economia"}], "maxCrawlPages": 10},
        timeout_secs=120
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    p(f"  OK: {len(items)} pages crawled")
    DATA["website_crawler"] = {"status": "OK", "count": len(items),
        "pages": [{"title": it.get("title","?"), "url": it.get("url","?"), "text_preview": str(it.get("text",it.get("markdown","")))[:200]} for it in items[:10]]}
except Exception as e:
    p(f"  X: {e}")
    DATA["website_crawler"] = {"status": "FAIL", "error": str(e)[:200]}

# SAVE
p("\n=== GUARDANDO ===")
with open("download_apify_results.json", "w", encoding="utf-8") as f:
    json.dump(DATA, f, indent=2, ensure_ascii=False, default=str)
p(f"OK: download_apify_results.json ({len(json.dumps(DATA, default=str))//1024} KB)")
