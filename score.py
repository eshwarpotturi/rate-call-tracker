"""Scores every call in data.json against what the central bank did. Run: python3 score.py"""
import json
from datetime import date

D = json.load(open("data.json"))
SRC = D["sources"]
STALE = D["stale_days"]
AS_OF = date.fromisoformat(D["as_of"])
day = date.fromisoformat


def history(bank, house):
    """All dated views of one house, oldest first."""
    out = []
    for s in bank["snapshots"]:
        if house in s["houses"]:
            out.append((day(SRC[s["src"]]["date"]), s["src"], s["houses"][house]))
    return sorted(out, key=lambda x: x[0])


def view_before(bank, house, cutoff):
    h = [x for x in history(bank, house) if x[0] < cutoff]
    return h[-1] if h else None


def call_for(bank, house, meeting_id, cutoff):
    """Returns (call, status, as_of, src, note). status: scored | none | revised | no_month | stale"""
    v = view_before(bank, house, cutoff)
    if not v:
        return None, "none", None, None, "No call found before this meeting."
    when, src, e = v
    age = (cutoff - when).days
    hikes, cuts = e.get("hikes", []), e.get("cuts", [])
    if e.get("unknown"):
        return None, "revised", when, src, e.get("note", "")
    if meeting_id in hikes:
        call = "hike"
    elif meeting_id in cuts:
        call = "cut"
    elif meeting_id in e.get("explicit_hold", []):
        call = "hold"
    elif "?" in hikes or "?" in cuts or ("Q1" in cuts and meeting_id in ("Jan", "Mar")):
        return None, "no_month", when, src, e.get("note", "Timing not specific enough to score.")
    else:
        call = "hold"
    if age > STALE:
        return call, "stale", when, src, f"Last view found is {age} days old, so it is not scored."
    return call, "scored", when, src, e.get("note", "")


def stance(e):
    if e.get("unknown"):
        return "unknown"
    if e.get("hikes"):
        return "hikes"
    if e.get("cuts"):
        return "cuts"
    return "hold"


out = {"as_of": D["as_of"], "stale_days": STALE, "banks": {}}
for key, bank in D["banks"].items():
    houses = []
    for s in bank["snapshots"]:
        for h in s["houses"]:
            if h not in houses:
                houses.append(h)
    over = {(o["house"], o["meeting"]): o for o in bank.get("overrides", [])}
    turn = next(m for m in bank["meetings"] if m["id"] == bank["turn"])
    rows = []
    for h in houses:
        cells, right, scored = {}, 0, 0
        for m in bank["meetings"]:
            call, status, when, src, note = call_for(bank, h, m["id"], day(m["decision"]))
            if (h, m["id"]) in over:
                status, note = "revised", over[(h, m["id"])]["reason"]
            ok = None
            if status == "scored":
                ok = call == m["outcome"]
                scored += 1
                right += ok
            cells[m["id"]] = {"call": call, "status": status, "ok": ok,
                              "as_of": when.isoformat() if when else None, "src": src, "note": note}
        # lead time on every meeting where the bank moved
        leads = {}
        for m in bank["meetings"]:
            if m["outcome"] == "hold":
                continue
            key_list = "hikes" if m["outcome"] == "hike" else "cuts"
            hist = [x for x in history(bank, h) if x[0] < day(m["decision"])]
            first = None
            for when, src, e in reversed(hist):
                if m["id"] in e.get(key_list, []):
                    first = (when, src)
                else:
                    break
            if first:
                leads[m["id"]] = {"days": (day(m["decision"]) - first[0]).days,
                                  "since": first[0].isoformat(), "src": first[1]}
        hist = history(bank, h)
        cut_views = [x for x in hist if x[2].get("cuts")]
        base = next((s for s in bank["snapshots"] if s.get("baseline")), None)
        gap = None
        if base and h in base["houses"] and base["houses"][h].get("ye") is not None:
            gap = round((bank["rate_now_mid"] - base["houses"][h]["ye"]) * 100)
        nxt = bank["next"]
        ncut = day(nxt["decision"]) if nxt["decision"] else AS_OF
        ncall, nstatus, nwhen, nsrc, nnote = call_for(bank, h, nxt["id"], max(ncut, AS_OF))
        rows.append({
            "house": h, "cells": cells, "right": right, "scored": scored, "leads": leads,
            "max_cuts": max((len(x[2]["cuts"]) for x in cut_views), default=0),
            "last_cut_view": cut_views[-1][0].isoformat() if cut_views else None,
            "last_cut_src": cut_views[-1][1] if cut_views else None,
            "base_gap_bp": gap,
            "base_stance": stance(base["houses"][h]) if base and h in base["houses"] else None,
            "timeline": [{"date": w.isoformat(), "stance": stance(e), "src": s, "note": e.get("note", ""),
                          "cuts": e.get("cuts", []), "hikes": e.get("hikes", [])} for w, s, e in hist],
            "next": {"call": ncall, "status": nstatus, "as_of": nwhen.isoformat() if nwhen else None, "src": nsrc, "note": nnote},
        })
    cons = {}
    for m in bank["meetings"]:
        tally = {}
        for r in rows:
            c = r["cells"][m["id"]]
            if c["status"] == "scored":
                tally[c["call"]] = tally.get(c["call"], 0) + 1
        top = max(tally, key=tally.get) if tally else None
        cons[m["id"]] = {"tally": tally, "majority": top, "ok": (top == m["outcome"]) if top else None,
                         "n": sum(tally.values()), "wrong": [r["house"] for r in rows
                                                            if r["cells"][m["id"]]["ok"] is False]}
    nt = {}
    for r in rows:
        if r["next"]["status"] == "scored":
            nt.setdefault(r["next"]["call"], []).append(r["house"])
    summary = {
        "houses": len(rows),
        "scored_calls": sum(r["scored"] for r in rows),
        "right_calls": sum(r["right"] for r in rows),
        "houses_with_miss": [r["house"] for r in rows if r["scored"] > r["right"]],
        "consensus_right": sum(1 for c in cons.values() if c["ok"]),
        "consensus_scored": sum(1 for c in cons.values() if c["ok"] is not None),
    }
    if any(s.get("baseline") for s in bank["snapshots"]):
        b = [r for r in rows if r["base_stance"]]
        gaps = sorted(r["base_gap_bp"] for r in b if r["base_gap_bp"] is not None)
        summary["base"] = {"n": len(b),
                           "cuts": sum(r["base_stance"] == "cuts" for r in b),
                           "hold": sum(r["base_stance"] == "hold" for r in b),
                           "hikes": sum(r["base_stance"] == "hikes" for r in b),
                           "median_gap_bp": gaps[len(gaps) // 2] if gaps else None}
    out["banks"][key] = {"rows": rows, "consensus": cons, "next_tally": nt, "summary": summary}

json.dump(out, open("scores.json", "w"), indent=1)
for k, b in out["banks"].items():
    print(k, b["summary"]); print("  next:", b["next_tally"])
    for r in b["rows"]:
        print("  %-24s %d/%d leads=%s lastcut=%s gap=%s" % (r["house"], r["right"], r["scored"],
              {m: v["days"] for m, v in r["leads"].items()}, r["last_cut_view"], r["base_gap_bp"]),
              "".join({True: "Y", False: "N", None: "-"}[c["ok"]] for c in r["cells"].values()))
