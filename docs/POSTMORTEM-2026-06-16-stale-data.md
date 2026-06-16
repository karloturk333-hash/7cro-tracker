# Postmortem — 7CRO chart silently froze (2026-06-16)

A learning write-up of the "data downloads but never updates the chart" bug,
how it was diagnosed, and the takeaways worth keeping.

---

## 1. The symptom

The dashboard chart stopped advancing. It was stuck at **2026-05-28** even though
the burza kept trading through June. The daily GitHub Actions cron kept running and
kept reporting **success (green)** every weekday — yet nothing in the repo changed
and the deployed Streamlit app never moved.

So from the outside it looked exactly like you described it:

> "the data gets downloaded, but it doesn't get pushed somehow."

That instinct was right — but the real problem was one step earlier than the push.

---

## 2. What actually happened

There were **three separate problems** stacked on top of each other. Only the first
caused the freeze; the other two are why it stayed invisible for weeks.

### Bug #1 (the cause): CSV format mismatch

The two CSVs involved were in **different formats**:

| | Separator | Decimal | Example price |
|---|---|---|---|
| Stored repo file (`data/sample/7cro_zse.csv`) | `;` semicolon | `,` comma | `37,90` |
| What the ZSE REST API returns | `,` comma | `.` dot | `36.70` |

`scripts/fetch_zse.py` read the API response with `sep=";"`. Because the API text
had no semicolons, pandas couldn't split it into columns — every downloaded row got
crammed into **one giant unparsed string** in a phantom 17th column. The merge step
then compared real rows against garbage rows, matched nothing useful, and the genuine
new June data was effectively thrown away.

So the data *was* downloaded. It just never survived parsing, so there was
genuinely nothing valid to push. Your mental model ("downloaded but not pushed")
pointed at the right area — the truth was "downloaded but destroyed during parse,
so the push had nothing to do."

### Bug #2 (the first mask): change was detected by row **count** only

The script decided "did anything change?" by checking whether the number of rows
went **up**. That means:

- Corrected values on a date that already existed → row count unchanged → "no change" → no commit.
- Even if parsing had worked, any same-day correction would have been ignored.

It only ever asked *"are there more rows?"*, never *"is the content different?"*.

### Bug #3 (the second mask): errors were swallowed as success

When the API call failed, the script printed a friendly message and
**returned exit code 0** — i.e. "success". GitHub Actions has no way to know the run
was actually a no-op disguised as a win, so the workflow badge stayed green and
nobody got alerted. Stale data with a green checkmark is the worst combination:
everything *looks* healthy.

---

## 3. How it was diagnosed

1. **Read the pipeline end to end** — workflow YAML → `fetch_zse.py` → `zse_api.py`
   → `loaders.py`. Cheap and fast; revealed the `sep=";"` assumption.
2. **Compared the two formats directly** — looked at the actual bytes of the stored
   CSV vs. a live API response. The semicolon-vs-comma / comma-vs-dot mismatch was
   obvious side by side, and the leftover phantom column in the committed CSV was the
   smoking gun that this had been broken since the *first* auto-pull.
3. **Ran it for real** — triggered the fetch against the live API and watched a real
   commit appear that moved the data from 2026-05-28 to 2026-06-15.

---

## 4. The fix

In `scripts/fetch_zse.py`:

- **Auto-detect the separator** and convert API dot-decimals into the repo's
  comma-decimal format before merging — so the downloaded rows actually parse.
- **Canonicalize to the 16 real ZSE columns**, dropping the phantom column and the
  junk row the old bug had baked in.
- **Content-based change detection** — commit/push on *any* real difference (new rows
  **or** corrected values), not just when the row count grows.
- **Fail loudly** — non-zero exit (with retries) on an API error or an unparsable
  response, so the workflow goes **red** instead of green-but-stale.
- **Diagnostics** — log the date range, latest date before/after, and row delta; put
  the latest data date in the commit message.
- **Regression tests** — 9 new tests for the previously untested fetch script.

Result of the verifying run:

```
chore: auto-update 7CRO data (2026-06-16, latest 2026-06-15)
1 file changed, 1035 insertions(+), 1025 deletions(-)
```

(The large diff is one-time cleanup: phantom column removed, decimals normalized,
backfill of the discarded June rows.)

---

## 5. Lessons worth keeping

1. **A green CI badge proves the job ran, not that it did its job.** If a task can
   "succeed" while doing nothing, it *will* eventually do nothing silently. Make the
   no-op path fail.
2. **Never swallow errors into a success exit code.** `except: return 0` is how
   broken pipelines hide. Let failures surface.
3. **Two CSVs are never "the same format" until you've checked the bytes.** Separator
   and decimal convention are part of the format, and they differ by locale/source.
   Detect, don't assume.
4. **Detect change by content, not by a proxy like row count.** A proxy answers a
   *different* question than the one you care about.
5. **The hardest bugs are the silent ones.** Add observability (what date range did we
   fetch? what's the latest date now?) so the next freeze announces itself.
6. **Reproduce against the real thing before declaring victory.** Reading the code
   found the bug; running it against the live API proved the fix.

---

## 6. One open follow-up

To let live fetches run from Claude Code web sessions (not just GitHub Actions), add
`rest.zse.hr` to this environment's network egress allowlist. Not required for the
production cron — that already has network access.
