# Vita Zelenko's health blog

A blog, not a publication. Vita is a 42-year-old health scientist who reads the literature
and writes in Ukrainian, in the first person, under her own name. There is no editorial
team and no masthead — that framing is retired everywhere, including in the prompts.

Site: longlife.media, TG: @long_life_media.

## Structure

| Path | Purpose |
|------|---------|
| `pipeline/` | Publishing pipeline (Python, 3 modes: generate/publish/digest) |
| `pipeline/stages/` | Pipeline stages (s0-s11) |
| `gatsby/` | Static site (Gatsby 5 + React) |
| `content/` | Markdown articles (Ukrainian) |
| `assets/character/` | Vita's turnaround and wardrobe sheets, fed to the image model |
| `scripts/` | Cron runner, utilities |
| `state/` | Runtime state (plans, teasers, posted, logs) |
| `.agents/` | Deep reference — [.agents/INDEX.md](.agents/INDEX.md) |

## Two hosts

Covers render through the Codex CLI, which is only installed and authenticated on
nero-prod, so writing happens there. Everything that touches the channel or the webroot
stays on faion-net — that separation is what stops the two machines publishing over each
other.

| Host | Mode | Cron (UTC) | What |
|------|------|------------|------|
| nero-prod | `generate` | `3 3 * * *` | The day's post, with its cover. Skips Sunday |
| nero-prod | `digest` | `0 6 * * 0` | Sunday: the week written as one long post |
| faion-net | `site` | `30 8 * * *`, `30 14 * * *` | Pull, `gatsby build`, rsync into the webroot |
| faion-net | `publish` | `5 9 * * *` | Send one post to TG (no LLM) |

`run-pipeline.sh` syncs with GitHub in both directions on every run: fetch, rebase
`--autostash`, push. That is the only channel between the hosts.

What goes out on which day, and what the blog is about:
[.agents/editorial.md](.agents/editorial.md).

## Key Commands

```bash
python3 -m pipeline generate -v           # Write the day's post
python3 -m pipeline generate --limit 1 -v # Explicit count, for testing a stage change
python3 -m pipeline publish -v            # Mechanical TG send
python3 -m pipeline digest -v             # The week as one long post
bash scripts/run-pipeline.sh site         # Rebuild the site (web host only)
```

## Quick Reference

- **Bot:** @nero_open_bot (shared)
- **Channel:** @long_life_media
- **Domain:** longlife.media (Cloudflare DNS -> faion-net nginx; `longlife.faion.net` is a
  redirect vhost). Webroot `/var/www/longlife.media`
- **LLM:** All stages use Claude Opus via Agent SDK
- **Author:** Віта Зеленко — first person, signed. No "редакція", no institutional "we"
- **Images:** Codex CLI (`LONGLIFE_IMAGE_PROVIDER=codex`), editorial photography

## Gotchas

- **Do not run `generate` or `digest` on faion-net.** Codex is not installed there, so
  every cover fails and the post can never go to the channel. Both are generation and both
  belong on nero-prod.
- **`publish` refuses a post whose page is not live yet** and moves down the queue. The
  site is rebuilt at 08:30 and the send is at 09:05; that gap is the whole reason the
  order is what it is.
- **`state/tg_published/` is the publish ledger and is tracked in git.** Never reset it to
  another host's version: the picker reads it to know what the channel has already had.
- The OpenAI image path still exists behind `LONGLIFE_IMAGE_PROVIDER=openai`, but the
  account's credits ran out on 22 July 2026 and `gpt-image-1` answers `insufficient_quota`.
- Dead RSS feeds (moz.gov.ua, ukrinform, unian, medicalnewstoday) return 404 and are
  tolerated. Working ones: bbc_health, who_news.

Deploy gotchas that cost a day each — the Gatsby query-result race, the Cloudflare purge,
a new frontmatter field breaking the build — are in
[.agents/nero-memory.md](.agents/nero-memory.md); read it before touching `deploy-gh.sh`.
