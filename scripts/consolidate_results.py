"""Consolidate all test results into nyx-full-test-results.json"""
import json

b1 = json.load(open("test_bloque1_results.json", encoding="utf-8"))
b2 = json.load(open("test_bloque2_results.json", encoding="utf-8"))
b3 = json.load(open("test_bloque3_results.json", encoding="utf-8"))

final = {
    "test_date": "2026-04-11",
    "bloque1_apis": b1,
    "bloque2_rss": b2,
    "bloque3_apify": b3,
}

with open("nyx-full-test-results.json", "w", encoding="utf-8") as f:
    json.dump(final, f, indent=2, ensure_ascii=False, default=str)
print("OK: nyx-full-test-results.json created")
