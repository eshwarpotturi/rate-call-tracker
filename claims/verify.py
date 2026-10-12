"""Gives every claim in claims.json a verdict against what the Fed actually did, and writes verdicts.json.
Run from the repo root: python3 claims/verify.py

Verdicts
  correct          deadline passed; the stated level/move happened (within 12.5 bp, i.e. the same target range)
  partly           deadline passed; one 25 bp move off, or right direction but wrong size or meeting
  wrong            deadline passed; off by two or more moves, or wrong direction
  untested         deadline still ahead and the claim can still come true
  needs_revision   deadline still ahead, but the facts since make it unreachable without a reversal
  unjudgeable      the claim has no level, size or date to test against
"""
import json
from datetime import date, timedelta

day = date.fromisoformat
C = json.load(open("claims/claims.json"))
P = json.load(open("claims/fed_path.json"))
AS_OF = day(P["as_of"])
START = (day(P["start"]["date"]), (P["start"]["lo"] + P["start"]["hi"]) / 2)
PATH = [START] + [(day(c["date"]), (c["lo"] + c["hi"]) / 2) for c in P["changes"]]
REMAINING = [day(d) for d in P["remaining_meetings"] if day(d) > AS_OF]
SEP_MEDIAN = {"2018-12-19": 2.875}  # median dot for end-2019 at the December 2018 meeting


def mid_on(d):
    """Midpoint of the target range in force at the end of day d."""
    return [m for when, m in PATH if when <= d][-1]


def changes_between(a, b):
    """Rate changes strictly after a and on or before b, as (date, bp)."""
    out, prev = [], None
    for when, m in PATH:
        if prev is not None and a < when <= b:
            out.append((when, round((m - prev) * 100)))
        prev = m
    return out


def grade(err_bp):
    e = abs(err_bp)
    return "correct" if e <= 12.5 else "partly" if e <= 25 else "wrong"


def open_status(target, deadline):
    """For a level claim whose deadline is ahead: can it still happen?"""
    now = mid_on(AS_OF)
    left = [m for m in REMAINING if m <= day(deadline)]
    gap = round((target - now) * 100)
    last = changes_between(day("2000-01-01"), AS_OF)[-1]
    against = gap != 0 and (gap > 0) != (last[1] > 0)
    if abs(gap) > 25 * len(left):
        return "needs_revision", f"Needs {gap:+d} bp with {len(left)} meetings left; the rate is {now:.3f}% now."
    if against:
        return "needs_revision", (f"Needs {gap:+d} bp, which reverses the Fed's {last[1]:+d} bp move of "
                                  f"{last[0]:%d %b %Y}; the rate is {now:.3f}% now.")
    if gap == 0:
        return "untested", f"Comes true if the Fed holds at both remaining meetings; the rate is {now:.3f}% now."
    return "untested", f"Needs {gap:+d} bp with {len(left)} meetings left; the rate is {now:.3f}% now."


def verify(c):
    k, dl = c["kind"], day(c["deadline"])
    made = day(c["made_on"])
    if k == "unjudgeable":
        return "unjudgeable", None, c["reason"], None
    if k == "dots":
        actual = round((SEP_MEDIAN[c["sep"]] - mid_on(day(c["sep"]))) / 0.25)
        v = "correct" if actual == c["hikes"] else "wrong"
        return v, f"Dots showed {actual} hikes", "Scored against the median dot published that day.", 0 if v == "correct" else (c["hikes"] - actual) * 25
    if k == "level":
        if dl > AS_OF:
            v, why = open_status(c["target"], c["deadline"])
            return v, f"{mid_on(AS_OF):.3f}% today", why, None
        actual = mid_on(dl)
        err = round((c["target"] - actual) * 100)
        return grade(err), f"{actual:.3f}%", f"Off by {err:+d} bp." if err else "Same target range.", err
    if k == "year_total":
        y = c["year"]
        actual = round((mid_on(day(f"{y}-12-31")) - mid_on(day(f"{y-1}-12-31"))) * 100)
        err = c["bp"] - actual
        return grade(err), f"{actual:+d} bp in {y}", f"Off by {err:+d} bp." if err else "Exact.", err
    if k == "move":
        m = day(c["meeting"])
        if m > AS_OF:
            return "untested", None, f"Meeting on {m:%d %b %Y} is still ahead.", None
        moved = sum(bp for _, bp in changes_between(made, m + timedelta(days=1)))
        if moved == c["bp"]:
            v = "correct"
        elif moved and (moved > 0) == (c["bp"] > 0):
            v = "partly"
        else:
            v = "wrong"
        note = "No change by that meeting." if not moved else f"Fed moved {moved:+d} bp by that meeting."
        if any(when < m and when > made for when, _ in changes_between(made, m)):
            note += " The move came early, at an unscheduled meeting."
        return v, f"{moved:+d} bp", note, c["bp"] - moved
    if k == "first_move":
        m = day(c["meeting"])
        sign = 1 if c["dir"] == "hike" else -1
        firsts = [w for w, bp in changes_between(made, day("2100-01-01")) if bp * sign > 0]
        if not firsts:
            return ("untested" if m > AS_OF else "wrong"), None, f"No {c['dir']} yet.", None
        f = firsts[0]
        if f > AS_OF:
            return "untested", None, "", None
        gap = (f - m).days
        v = "correct" if abs(gap) <= 3 else "partly" if abs(gap) <= 60 else "wrong"
        when = "on time" if v == "correct" else f"{abs(gap)} days {'later' if gap > 0 else 'earlier'} than called"
        return v, f"First {c['dir']}: {f:%d %b %Y}", f"Came {when}.", gap
    raise ValueError(k)


rows = []
for c in C["claims"]:
    v, actual, why, err = verify(c)
    rows.append({**c, "verdict": v, "actual": actual, "why": why, "err": err,
                 "horizon_days": (day(c["deadline"]) - day(c["made_on"])).days})

houses = {}
for r in rows:
    h = houses.setdefault(r["house"], {"house": r["house"], "correct": 0, "partly": 0, "wrong": 0,
                                       "untested": 0, "needs_revision": 0, "unjudgeable": 0})
    h[r["verdict"]] += 1
for h in houses.values():
    h["judged"] = h["correct"] + h["partly"] + h["wrong"]
    h["score"] = round((h["correct"] + 0.5 * h["partly"]) / h["judged"], 3) if h["judged"] else None

years = {}
for r in rows:
    if r["verdict"] in ("correct", "partly", "wrong"):
        y = years.setdefault(r["deadline"][:4], {"year": r["deadline"][:4], "correct": 0, "partly": 0, "wrong": 0})
        y[r["verdict"]] += 1

buckets = [("Up to 2 months", 0, 60), ("2 to 6 months", 61, 182), ("6 to 12 months", 183, 366), ("Over a year", 367, 99999)]
horizon = []
for name, lo, hi in buckets:
    b = [r for r in rows if r["verdict"] in ("correct", "partly", "wrong") and lo <= r["horizon_days"] <= hi]
    horizon.append({"bucket": name, "n": len(b), "correct": sum(r["verdict"] == "correct" for r in b),
                    "partly": sum(r["verdict"] == "partly" for r in b), "wrong": sum(r["verdict"] == "wrong" for r in b)})

tally = {}
for r in rows:
    tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1

out = {"as_of": C["as_of"], "domain": C["domain"], "extracted_by": C["extracted_by"], "sources": C["sources"],
       "rate_now": mid_on(AS_OF), "remaining_meetings": [m.isoformat() for m in REMAINING],
       "tally": tally, "houses": sorted(houses.values(), key=lambda h: (-(h["score"] or -1), -h["judged"])),
       "years": sorted(years.values(), key=lambda y: y["year"]), "horizon": horizon, "claims": rows}
json.dump(out, open("claims/verdicts.json", "w"), indent=1)

print(len(rows), "claims", tally)
for b in horizon:
    print(" ", b)
for y in out["years"]:
    print(" ", y)
for h in out["houses"]:
    print("  %-30s judged=%2d score=%s  c%d p%d w%d u%d nr%d" % (h["house"], h["judged"], h["score"], h["correct"],
          h["partly"], h["wrong"], h["untested"], h["needs_revision"]))
