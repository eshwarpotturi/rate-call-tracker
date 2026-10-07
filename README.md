# Rate Call Tracker

Who called the 2026 turns at the US Federal Reserve, the European Central Bank and the Reserve Bank of India, and how many days ahead they called them.

**Live page:** https://eshwarpotturi.github.io/rate-call-tracker/

Data runs to 7 October 2026, the day the RBI raised its repo rate to 5.50%.

## What it is

A one-page scorecard. For each central bank it shows:

- **Next decision**: what each house expects, who the outlier is, and what to write in the pre-meeting note.
- **Who moved first**: days between a house's first reported call for a rate move and the move itself.
- **When each house changed its mind** (Fed): every house's published stance through the year, as a timeline.
- **Meeting by meeting**: the last view each house held before each decision, marked right or wrong.
- **Evidence**: every dated view behind the tab, each linked to the report it came from.

## Why

Macro notes say "consensus expects a hold". They rarely say whose view has earned the most weight. Checking that by hand means collecting each house's preview before a meeting and going back afterwards, which usually does not happen.

The main finding from 2026: on the day of a decision almost everyone is right (87 of 91 scored calls). A hit-rate table therefore ranks nearly every house the same. What separates them is lead time. Before the Fed's September hike, BofA and Deutsche Bank had it 86 days ahead; Morgan Stanley had it 1 day ahead.

## Who it is for

SG Analytics, whose clients are asset managers, wealth managers and sell-side teams in the US and Europe. The Fed and ECB tabs use the houses those clients already read. Uses:

- one track-record line in each pre-meeting macro update or CIO newsletter;
- an alert when a house with a good record breaks from the pack;
- a quarterly scorecard a client can use to decide which sell-side research to keep paying for.

## How it works

| File | What it does |
|---|---|
| `data.json` | Every dated view, by house, with its source. Edit this to add a house, a meeting or a bank. |
| `score.py` | Scores each view against the decision and writes `scores.json`. |
| `template.html` | The page layout and commentary. |
| `build.py` | Puts data and scores into the template and writes `index.html`. |

To update: edit `data.json`, then run `python3 score.py && python3 build.py`. `index.html` is self-contained, so GitHub Pages can serve it directly.

### Scoring rules

1. A call is the last published view found before the decision date.
2. A view older than 90 days at the decision is stale and not scored.
3. If a report says a house revised its forecast without saying to what, the house is not scored until its next dated view.
4. Lead time counts back from the decision to the first report of the house forecasting that move at that meeting, with no later report reversing it.

## Questions you will get

**Does this already exist?** Partly. Bloomberg ranks economists by forecast accuracy on its terminal. FocusEconomics, Consensus Economics and LSEG give annual accuracy awards. Those are paywalled or yearly, and they score the final number. As far as we know none publishes lead time before a turn.

**Is this not just asking ChatGPT?** A chat tool can attempt it once, with no record of where each number came from. The value here is the dated, linked dataset and a scoring rule that gives the same answer every time it runs.

**Does weighting by track record beat the consensus?** Not shown. The majority view was right at every meeting in this set, so weighting would not have changed the meeting-eve answer once. One year holds one turn per bank. A real test needs 2022 to 2025.

**How complete is it?** Uneven. The Fed tab covers 15 houses from Reuters broker tables. The ECB tab has 9 houses and the RBI tab 6, from individual reports. A missing house means no dated call was found, not that it made none.

**Where does the data come from?** Public news reports of each house's forecast, mostly Reuters tables republished by other outlets. Every row links to its source.

## Check before sending outside

- Two Fed tables (30 March and 27 May) were read from search listings because the hosting page would not open. Open those two links and confirm the rows.
- ECB preview dates for Deutsche Bank, TD Securities and ING are approximate (week of 20 July).
- Goldman's change of its ECB call from April to June has no date in the source, so its April call is not scored.
- Morgan Stanley's 174-day lead on the ECB's September hike rests on one March report.
- The 29 October ECB date and the 27-28 October Fed date should be confirmed against each bank's calendar.

Not investment advice.
