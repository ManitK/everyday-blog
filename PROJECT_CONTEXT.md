# Everyday Blog: Project Context

## What this is

A small Python daily digest for personal reading. It checks configured engineering/blog sources, finds posts newer than the last successful run, asks Claude for a short plain-language gist, and sends one ntfy notification to an iPhone.

It is a scheduled script, not a server. Run locally with:

```bash
python main.py
```

GitHub Actions runs it daily at 06:00 IST (`00:30 UTC`).

## Runtime flow

1. Load `.env` locally, or GitHub Actions secrets in CI.
2. Load blog definitions from `config.yaml`.
3. Discover posts through RSS/Atom, sitemap, HTML, or configured public Next.js page data.
4. Keep posts newer than `state.json`'s `last_successful_run`.
5. Use a feed excerpt when useful; otherwise fetch only the new article page and extract at most 200 words.
6. Make exactly one Claude summary request per selected article.
7. Build one ntfy digest and publish it.
8. Update `state.json` only after the whole run succeeds.

## Important files

- `main.py` — entry point.
- `config.yaml` — public source definitions and scheduler-related settings. Safe to commit.
- `everyday_blog/app.py` — pipeline orchestration, state rules, concurrency.
- `everyday_blog/discovery.py` — shared feed, sitemap, HTML, and Next.js discovery helpers.
- `everyday_blog/extract.py` — short article excerpt extraction.
- `everyday_blog/claude.py` — concise, plain-language Claude prompt.
- `everyday_blog/notify.py` — single compact plain-text ntfy message.
- `everyday_blog/state.py` — timestamp-only state read/write.
- `.github/workflows/daily-digest.yml` — scheduled GitHub Actions job; commits updated state after success.

## Secrets and state

- Local secrets are in ignored `.env`: `ANTHROPIC_API_KEY`, `NTFY_TOPIC`, optional `CLAUDE_MODEL`.
- GitHub uses repository Secrets with the same names.
- Never commit `.env` or API keys.
- `state.json` stores only the last successful timestamp. GitHub Actions force-adds it after successful runs so later runs continue from the correct time.

## Constraints to preserve

- Do not add a database or an agent framework.
- Never send a full article to Claude; send title/source/URL plus a maximum 200-word excerpt only.
- Keep one Claude call per selected article.
- Keep one ntfy digest per successful run; do not send anything when there are no new posts.
- A failure must not advance the timestamp, so articles are not silently skipped.
- Blog-specific details belong in `config.yaml`; keep discovery code shared and generic rather than adding per-site loops.
- The ntfy digest must remain compact enough for a normal iPhone push notification; raw HTTPS URLs are tappable.
