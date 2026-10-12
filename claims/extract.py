"""Extracts Fed rate forecasts from one article into the claims.json format, using an LLM through Straive's LLM Foundry.

Usage:
  export LLMFOUNDRY_TOKEN=...          # from https://llmfoundry.straive.com/code
  python3 claims/extract.py article.txt --date 2025-01-15 --src rt2501 [--model gpt-4.1-mini]

Prints a JSON list of claims. Review them, then add them to claims/claims.json and run claims/verify.py.
Uses only the Python standard library. Nothing is sent anywhere except LLM Foundry.
"""
import argparse
import json
import os
import urllib.request

URL = "https://llmfoundry.straive.com/openai/v1/chat/completions"

PROMPT = """You extract testable forecasts about the US Federal Reserve's policy rate (fed funds target range)
from one news article. The article was published on {date}.

Return every forecast made by a named forecaster (a bank, broker, research house, survey or the FOMC itself).
Skip market pricing, reporters' own views and statements about the past.

Each forecast is one of these kinds:
- level: the rate will be at a level by a date. Give "target" as the midpoint of the range in percent
  (3.75%-4.00% -> 3.875). If only one number is given, say whether it is the top of the range or the midpoint in "basis".
- move: a change of a stated size at a stated meeting. Give "meeting" (YYYY-MM-DD) and "bp" (+25, -50, ...).
- first_move: when the first hike or cut comes. Give "dir" ("hike" or "cut") and "meeting".
- year_total: net change over a calendar year. Give "year" and "bp".
- dots: what the Fed's own projections will show. Give "sep" (meeting date), "year" and "hikes".
- unjudgeable: a view with no level, size or date that could be checked. Give "reason".

For every forecast also give: "house", "quote" (the shortest phrase from the article, at most 15 words, that states it),
"deadline" (YYYY-MM-DD by which it can be checked; end of year = 31 Dec) and "stated" (a short plain restatement).
Return JSON: {{"claims": [ ... ]}}.

ARTICLE:
{text}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--date", required=True, help="publication date, YYYY-MM-DD")
    ap.add_argument("--src", required=True, help="source key to store with each claim")
    ap.add_argument("--model", default="gpt-4.1-mini")
    a = ap.parse_args()
    token = os.environ["LLMFOUNDRY_TOKEN"]
    body = {"model": a.model, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": PROMPT.format(date=a.date, text=open(a.article).read())}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {token}:rate-call-tracker"})
    with urllib.request.urlopen(req, timeout=120) as r:
        reply = json.load(r)["choices"][0]["message"]["content"]
    claims = json.loads(reply)["claims"]
    for c in claims:
        c["made_on"], c["src"] = a.date, a.src
    print(json.dumps(claims, indent=1))


if __name__ == "__main__":
    main()
