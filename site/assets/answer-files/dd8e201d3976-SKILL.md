---
name: ycombinator-front-stories
description: "Extract front-page story listings from Hacker News (news.ycombinator.com) including title, URL, points, author, age, and comment count via DOM extraction, with URL pagination across pages. Use when user mentions Hacker News, HN, ycombinator, news.ycombinator.com, front page stories, HN top posts, HN listings, or asks to grab, fetch, pull, scrape, collect, or monitor stories, posts, articles, or links from Hacker News. Also applies to paginating through HN front pages beyond the first 30 items."
---

# Hacker News — Front-Page Story Extraction

> Extract story listings (title, URL, score, author, age, comments) from the current Hacker News page DOM, with URL-based pagination to subsequent pages.

## Language

All process output to user (progress updates, process notifications) follows the user's language.

## Objective

Extract the list of stories currently displayed on a Hacker News listing page, including rank, title, destination URL, source site, score, submitter, age, and comment count, and support walking to subsequent pages via the "More" link.

## Prerequisites

- Target page is already open in the browser: `https://news.ycombinator.com/` (or `https://news.ycombinator.com/news?p={page}` for later pages)
- No login required for reading the front page; voting, commenting, and submission features are out of scope.

## Pre-execution Checks

### 1. Tool Readiness

If browser-act has been confirmed available in the current session → skip this step.

Invoke `browser-act` via Skill tool to load usage. If installation or configuration issues arise, follow its guidance to resolve then retry.

## Capability Components

> This Skill's operational boundary = what the user can manually do in their browser. It only reads data already displayed to the user on the page, never bypassing authentication or access controls. Its role is equivalent to copy-pasting on the user's behalf — the data is already on screen, automation merely saves time. JS code is encapsulated in Python files under the `scripts/` directory, invoked via `eval "$(python scripts/xxx.py {params})"`. `$(...)` is bash syntax; it is recommended to use the bash tool for execution.

Below are all atomic capabilities discovered and verified during the exploration phase, listed by command template with parameters. Simply invoke them as needed — no need to read `scripts/*.py` source code or re-verify. Only inspect scripts when execution fails for troubleshooting. Combine freely as needed during execution.

### DOM: front-page story list

Extract all stories currently rendered on the page:

`eval "$(python scripts/extract-stories.py)"`

Optional parameters:
- --limit: maximum number of stories to return; default 0 (no limit, returns all stories on the page).

Output example:
```json
{
  "count": 30,
  "items": [
    {
      "id": "12345678",
      "rank": 1,
      "title": "Example story title",
      "url": "https://example.com/article",
      "site": "example.com",
      "score": 87,
      "user": "someuser",
      "age": "2 hours ago",
      "comments": 30
    }
  ]
}
```

Field notes:
- `id`: Hacker News item id from the row `id` attribute; null if absent.
- `rank`: position on the current page, parsed from the `.rank` element; null if absent.
- `site`: source domain shown next to the title; null for self-posts (Ask HN, Show HN text posts) that have no external link.
- `score`: points as integer; null when the row has no score (e.g., job posts).
- `comments`: comment count as integer; 0 when the link reads "discuss" (no comments yet); null if no comment link is present.
- `age`: relative time text as displayed (e.g., "2 hours ago"); this is a snapshot at page-load time.

Error handling: when no `tr.athing.submission` rows are found, returns `{"error": true, "message": "..."}` — check that the browser is on a Hacker News listing page and the page has finished loading, then retry once.

### DOM: next-page link

Read the "More" link to obtain the next page URL:

`eval "$(python scripts/get-next-page.py)"`

Output example:
```json
{
  "hasNext": true,
  "nextUrl": "https://news.ycombinator.com/news?p=2"
}
```

When on the last available page:
```json
{
  "hasNext": false,
  "nextUrl": null,
  "message": "No morelink found; reached the last available page."
}
```

### Composite: extract stories across multiple pages

Walk pages sequentially, extracting stories from each and following the "More" link:

1. `navigate https://news.ycombinator.com/` → `wait stable`
2. `eval "$(python scripts/extract-stories.py)"` → record items
3. `eval "$(python scripts/get-next-page.py)"` → read `nextUrl`
4. If `hasNext` is true: `navigate {nextUrl}` → `wait stable` → repeat from step 2
5. Stop when `hasNext` is false or the desired page count / item count is reached

Merge: items are already unique by `id`; if re-running after a page refresh, deduplicate by `id` before appending.

## Pagination

**URL Pagination**: The "More" link (`a.morelink`) carries the next page as a relative query (`?p=2`, `?p=3`, …), resolved against the current listing URL. Next page link selector: `a.morelink`. Termination: `hasNext` is false (no morelink present), or the configured maximum page/item count is reached. Each page contains up to 30 stories.

## Success Criteria

- `result count >= 1` on a non-empty listing page.
- Core field non-null rate = 100% for `id`, `rank`, `title` on every extracted item (these are always present for story rows).
- Extracted `id` and `title` for the first 5 items match the first 5 rows visible on the page.
- Pagination: navigating to the `nextUrl` returned by page N yields stories whose `rank` values start at `30*N + 1` and do not duplicate any `id` from page N.

## Known Limitations

- Each page contains up to 30 stories; collecting more requires walking pages via the "More" link.
- `score` and `comments` are snapshots at page-load time and change as other users vote and comment; re-navigate to refresh.
- Self-posts (Ask HN, etc.) have `site: null` and may have `score: null` for job postings.
- The `age` field is display text (relative time), not an absolute timestamp; the absolute time is available in the `title` attribute of the `.age` span but is not extracted by this component.

## Execution Efficiency

- **Batch orchestration**: Write a bash script to loop through the command templates serially within a single session; do not parallelize within one browser (prone to triggering anti-scraping restrictions). Add a short delay (e.g., 1–2 seconds) between page navigations to be respectful to the site.
- **Test before batch execution**: After writing a batch script, you must first test with 1–2 pages to verify the script runs correctly; only then run the full batch. Never skip testing and execute in batch directly.
- **Error resumption**: Save results page by page during batch processing; on failure, resume from the last successfully saved page rather than starting over.
- **Idempotency**: When accumulating results across runs, key items by `id` and skip ids already collected to avoid duplicates.

## Experience Notes

Path: `{working-directory}/browser-act-skill-forge-memories/hackernews-stories-ycombinator-front-stories.memory.md` (working directory is determined by the Agent running the Skill, typically the project root or current working directory)

**Before execution**: If the file exists, read it first — it records unexpected situations encountered during past executions (e.g., a strategy has become ineffective); adjust strategy order accordingly.

**After execution**: If an unexpected situation is encountered (strategy became ineffective, page redesigned, anti-scraping upgraded, better path discovered), append a line:
`{YYYY-MM-DD}: {what happened} → {conclusion}`

Normal execution does not write to the file. Do not record what keywords were used or how many results were returned — those are task outputs, not experience.
