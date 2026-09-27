# Everyday Blog

A once-per-day local Python digest: discovers recent posts from configured blogs, sends only a short excerpt to Claude for a 1–2 sentence gist, and publishes one ntfy notification.

## Setup

```bash
cd everyday-blog
.venv/bin/python main.py
```

`config.yaml` contains only public source URLs and is safe to commit. `state.json` and `.env` are ignored locally: the GitHub workflow force-adds only `state.json` after a successful run, while `.env` and credentials are never committed. The first successful run establishes the starting timestamp; it does not backfill existing posts. Set `last_successful_run` in `state.json` manually if a backfill is wanted.

## Reliability behavior

- A feed is preferred, followed by a sitemap and then configured blog HTML. One usable discovery method is sufficient for each blog.
- For JavaScript-rendered sites with public Next.js data, `next_data` maps a configured JSON path and field names into the same article format as feeds and HTML.
- Article pages are fetched only after a post passes the timestamp filter. Feed excerpts are used first when meaningful.
- Claude receives a title, source, URL, and at most 200 excerpt words; there is exactly one Claude request for every article being summarized.
- New articles are processed concurrently (`article_workers`, default `4`) before one ordered daily digest is sent. Lower it if an API rate limit is encountered.
- Failures are logged per blog and do not stop other blogs. To ensure a failed blog cannot be silently skipped, the single timestamp is advanced only when every configured blog, all selected article summaries, notification (if needed), and state write preparation succeed. Thus a later run may retry already-delivered items after a failed run; this is the tradeoff of deliberately having no article database.
- A successful run with no articles does not contact ntfy.

## GitHub Actions: 06:00 IST daily

The included workflow runs at `00:30 UTC`, which is `06:00 IST`, and can also be started manually from the Actions tab. Before pushing the project to GitHub, add these repository secrets under **Settings → Secrets and variables → Actions**:

- `ANTHROPIC_API_KEY`
- `NTFY_TOPIC` — the topic name only, for example `my-blog-digest-...`
- `CLAUDE_MODEL` — optional; set it to `claude-haiku-4-5-20251001` to match the local setup

Do not add `.env` to GitHub. GitHub-hosted runners are ephemeral, so the workflow force-adds and commits only `state.json` after a successful run. This timestamp-only file has no credentials and prevents the next daily run from treating every post as new. A failed run does not reach that commit step, leaving the prior timestamp intact for a later retry.

To enable it:

```bash
git init                       # only if this folder is not already a Git repository
git add .
git commit -m "Add daily blog digest"
git branch -M main
git remote add origin <your-GitHub-repository-URL>
git push -u origin main
```

After adding the secrets, open **Actions → Daily blog digest → Run workflow** once. The first successful GitHub run establishes or persists the current timestamp; later scheduled runs send a digest only when new posts exist.
