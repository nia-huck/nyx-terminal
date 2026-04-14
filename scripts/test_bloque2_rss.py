"""Nyx Terminal - Bloque 2: Test de RSS Feeds"""
import httpx
import feedparser
import json

TIMEOUT = 30
ALL_RESULTS = {}

feeds = [
    ("Ambito Economia", "https://www.ambito.com/rss/pages/economia.xml"),
    ("El Cronista", "https://www.cronista.com/files/rss/news.xml"),
    ("El Economista Finanzas", "https://eleconomista.com.ar/finanzas/feed/"),
    ("El Economista Economia", "https://eleconomista.com.ar/economia/feed/"),
    ("El Economista Internacional", "https://eleconomista.com.ar/internacional/feed/"),
]

print("\n=== RSS FEEDS ===")
for fname, furl in feeds:
    try:
        with httpx.Client(timeout=TIMEOUT, verify=False, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}) as c:
            r = c.get(furl)

        if "html" in r.headers.get("content-type", "").lower() and "<rss" not in r.text[:500].lower() and "<feed" not in r.text[:500].lower():
            print(f"  X {fname}: HTTP {r.status_code} pero devuelve HTML, no RSS/XML")
            ALL_RESULTS[fname] = {"status": "FAIL", "note": "Returns HTML not RSS", "http": r.status_code}
            continue

        feed = feedparser.parse(r.text)
        items = feed.entries
        if items:
            latest_title = items[0].get("title", "Sin titulo")
            latest_date = items[0].get("published", items[0].get("updated", "sin fecha"))
            print(f"  OK {fname}: {len(items)} items")
            print(f"     Ultimo: {latest_title[:90]}")
            print(f"     Fecha:  {latest_date}")
            ALL_RESULTS[fname] = {
                "status": "OK",
                "items_count": len(items),
                "latest_title": latest_title,
                "latest_date": latest_date,
                "all_titles": [it.get("title", "?") for it in items[:10]]
            }
        else:
            print(f"  X {fname}: Feed parseado pero 0 items (HTTP {r.status_code})")
            ALL_RESULTS[fname] = {"status": "FAIL", "note": "0 items parsed", "http": r.status_code}
    except Exception as e:
        print(f"  X {fname}: {e}")
        ALL_RESULTS[fname] = {"status": "FAIL", "error": str(e)}

with open("test_bloque2_results.json", "w", encoding="utf-8") as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False, default=str)
print("\n>> Guardado en test_bloque2_results.json")
