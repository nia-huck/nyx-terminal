"""Nyx Terminal — MCP Server para Apify.

Expone los actores de Apify como tools MCP que el agente puede invocar.
Implementa Model Context Protocol (MCP) sobre stdio o HTTP.

Este modulo puede correr standalone como servidor MCP:
    python -m core.mcp_apify

O ser usado internamente por el agente como wrapper MCP-compatible.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
load_dotenv(override=True)


# ═══════════════════════════════════════════════════════
#  MCP TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════

MCP_TOOLS = [
    {
        "name": "apify_web_search",
        "description": "Search the web in real-time using Apify RAG Web Browser. Returns titles, URLs, and text content from web pages matching the query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (in Spanish for Argentine economic data)"},
                "max_results": {"type": "integer", "description": "Maximum results (1-10)", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "apify_twitter_search",
        "description": "Search Twitter/X in real-time using Apify scraper. Returns tweets matching search terms.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "terms": {"type": "array", "items": {"type": "string"}, "description": "Search terms"},
                "max_tweets": {"type": "integer", "description": "Maximum tweets (1-50)", "default": 20},
            },
            "required": ["terms"],
        },
    },
    {
        "name": "apify_news_scrape",
        "description": "Scrape news articles from Argentine media using Apify article extractor. Returns full article text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "urls": {"type": "array", "items": {"type": "string"}, "description": "URLs to scrape"},
            },
            "required": ["urls"],
        },
    },
    {
        "name": "apify_reddit_search",
        "description": "Search Reddit for posts and comments using Apify Reddit scraper.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subreddits": {"type": "array", "items": {"type": "string"}, "description": "Subreddits to search (e.g. merval, argentina)"},
                "query": {"type": "string", "description": "Search query within subreddits"},
                "max_posts": {"type": "integer", "description": "Maximum posts (1-30)", "default": 15},
            },
            "required": ["subreddits"],
        },
    },
]

# Cost estimates per actor run
COST_MAP = {
    "apify_web_search": 0.02,
    "apify_twitter_search": 0.05,
    "apify_news_scrape": 0.03,
    "apify_reddit_search": 0.02,
}


# ═══════════════════════════════════════════════════════
#  MCP TOOL EXECUTION
# ═══════════════════════════════════════════════════════

class ApifyMCPServer:
    """Ejecuta tools MCP de Apify. Puede persistir resultados al DB."""

    def __init__(self, apify_token: str | None = None, persist_to_db: bool = True):
        self.token = apify_token or os.getenv("APIFY_TOKEN", "")
        self.persist = persist_to_db
        self._client = None
        self.total_spent = 0.0
        self.total_calls = 0

    @property
    def client(self):
        if self._client is None and self.token:
            from apify_client import ApifyClient
            self._client = ApifyClient(self.token)
        return self._client

    def list_tools(self) -> list[dict]:
        return MCP_TOOLS

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Ejecuta una tool MCP y retorna el resultado."""
        if not self.client:
            return {"error": "Apify token not configured", "isError": True}

        handlers = {
            "apify_web_search": self._web_search,
            "apify_twitter_search": self._twitter_search,
            "apify_news_scrape": self._news_scrape,
            "apify_reddit_search": self._reddit_search,
        }

        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}", "isError": True}

        try:
            result = handler(arguments)
            self.total_spent += COST_MAP.get(name, 0)
            self.total_calls += 1
            return result
        except Exception as e:
            return {"error": str(e)[:300], "isError": True}

    def _web_search(self, args: dict) -> dict:
        query = args.get("query", "")
        max_results = min(args.get("max_results", 5), 10)

        run = self.client.actor("apify/rag-web-browser").call(
            run_input={"query": query, "maxResults": max_results},
            timeout_secs=60,
        )
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        results = []
        for it in items:
            results.append({
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "text": it.get("markdown", it.get("text", ""))[:2000],
            })

        # Persist to DB
        if self.persist and results:
            self._persist_noticias(results, f"mcp_web:{query[:40]}")

        return {"results": results, "cost_usd": COST_MAP["apify_web_search"]}

    def _twitter_search(self, args: dict) -> dict:
        terms = args.get("terms", [])
        max_tweets = min(args.get("max_tweets", 20), 50)

        run = self.client.actor("xtdata/twitter-x-scraper").call(
            run_input={"searchTerms": terms, "maxTweets": max_tweets},
            timeout_secs=90,
        )
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        tweets = []
        for it in items:
            tweets.append({
                "text": it.get("full_text", it.get("text", "")),
                "author": (it.get("author", {}).get("screen_name", "")
                           if isinstance(it.get("author"), dict) else str(it.get("author", ""))),
                "likes": it.get("favorite_count", it.get("likeCount", 0)),
                "retweets": it.get("retweet_count", it.get("retweetCount", 0)),
                "created_at": it.get("created_at", ""),
                "url": it.get("url", ""),
            })

        # Persist to DB
        if self.persist and items:
            self._persist_tweets(items, ",".join(terms)[:40])

        return {"tweets": tweets, "cost_usd": COST_MAP["apify_twitter_search"]}

    def _news_scrape(self, args: dict) -> dict:
        urls = args.get("urls", [])[:5]  # Max 5 URLs

        run = self.client.actor("lukaskrivka/article-extractor-smart").call(
            run_input={"articleUrls": [{"url": u} for u in urls]},
            timeout_secs=60,
        )
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        articles = []
        for it in items:
            articles.append({
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "text": it.get("text", "")[:3000],
                "date": it.get("date", ""),
                "author": it.get("author", ""),
            })

        if self.persist and articles:
            self._persist_noticias(articles, "mcp_scrape")

        return {"articles": articles, "cost_usd": COST_MAP["apify_news_scrape"]}

    def _reddit_search(self, args: dict) -> dict:
        subs = args.get("subreddits", [])
        query = args.get("query", "")
        max_posts = min(args.get("max_posts", 15), 30)

        run = self.client.actor("trudax/reddit-scraper-lite").call(
            run_input={
                "startUrls": [{"url": f"https://www.reddit.com/r/{s}/search/?q={query}"} for s in subs],
                "maxItems": max_posts,
            },
            timeout_secs=60,
        )
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        posts = []
        for it in items:
            posts.append({
                "title": it.get("title", ""),
                "body": it.get("body", "")[:1500],
                "url": it.get("url", ""),
                "score": it.get("score", 0),
                "subreddit": it.get("subreddit", ""),
                "author": it.get("author", ""),
            })

        if self.persist and items:
            self._persist_reddit(items)

        return {"posts": posts, "cost_usd": COST_MAP["apify_reddit_search"]}

    # ── DB Persistence ────────────────────────────

    def _persist_noticias(self, items: list[dict], fuente: str):
        try:
            from core.context_writer import ingerir_noticias
            ingerir_noticias(items, fuente=fuente)
        except Exception:
            pass

    def _persist_tweets(self, raw_items: list[dict], query: str):
        try:
            from core.context_writer import ingerir_tweets
            ingerir_tweets(raw_items, query=query, fuente="mcp_apify")
        except Exception:
            pass

    def _persist_reddit(self, items: list[dict]):
        try:
            from core import db
            for it in items:
                db.insert_reddit(
                    post_id=it.get("url", ""),
                    titulo=it.get("title", "")[:500],
                    cuerpo=it.get("body", "")[:5000],
                    autor=it.get("author", ""),
                    score=it.get("score", 0),
                    subreddit=it.get("subreddit", ""),
                    url=it.get("url"),
                    fuente="mcp_apify",
                )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
#  MCP JSON-RPC PROTOCOL (stdio)
# ═══════════════════════════════════════════════════════

def handle_mcp_request(request: dict, server: ApifyMCPServer) -> dict:
    """Procesa un request MCP JSON-RPC."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "nyx-apify-mcp", "version": "1.0.0"},
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": server.list_tools()},
        }

    elif method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = server.call_tool(name, arguments)

        if result.get("isError"):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result["error"]}], "isError": True},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}]},
        }

    elif method == "notifications/initialized":
        return None  # No response needed for notifications

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def run_stdio_server():
    """Corre el servidor MCP sobre stdio (para integración con Claude Desktop, etc)."""
    server = ApifyMCPServer()
    print("nyx-apify-mcp server started", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_mcp_request(request, server)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            pass
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)[:200]},
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
