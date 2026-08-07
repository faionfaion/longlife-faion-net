# LongLife Media — Healthy Lifestyle for Ukrainians

Evidence-based health media in Ukrainian. Site: longlife.faion.net, TG: @long_life_media.

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
| `admin/` | Flask admin panel |

## Two hosts

Covers render through the Codex CLI, which is only installed and authenticated on
nero-prod, so writing happens there. Everything that touches the channel or the webroot
stays on faion-net — that separation is what stops the two machines publishing over each
other.

| Host | Mode | Cron (UTC) | What |
|------|------|------------|------|
| nero-prod | `generate` | `3 3 * * *` | Editorial plan, 8-10 articles with covers, commit, push |
| faion-net | `publish` | `5 9,12,15,18 * * *` | Pick a pre-generated article, send to TG (no LLM) |
| faion-net | `digest` | `43 20 * * *` | Compile the day's articles into an evening digest |
| faion-net | `site` | `30 5 * * *` | Pull, `gatsby build`, rsync into the webroot |

`run-pipeline.sh` syncs with GitHub in both directions on every run: fetch, rebase
`--autostash`, push. That is the only channel between the hosts.

## Key Commands

```bash
python3 -m pipeline generate -v          # Batch generate all articles
python3 -m pipeline generate --limit 1 -v  # One article, for testing a stage change
python3 -m pipeline publish -v           # Mechanical TG publish
python3 -m pipeline digest -v            # Evening digest
bash scripts/run-pipeline.sh site        # Rebuild the site (web host only)
```

## Quick Reference

- **Bot:** @nero_open_bot (shared)
- **Channel:** @long_life_media
- **Domain:** longlife.faion.net (Cloudflare DNS -> faion-net nginx)
- **LLM:** All stages use Claude Opus via Agent SDK
- **Images:** Codex CLI (`LONGLIFE_IMAGE_PROVIDER=codex`), editorial photography

## Gotchas

- **Do not run `generate` on faion-net.** Codex is not installed there, so every cover
  fails and the articles it writes can never go to the channel.
- **`state/tg_published/` is the publish ledger and is tracked in git.** Never reset it to
  another host's version: the picker reads it to know what the channel has already had.
- The OpenAI image path still exists behind `LONGLIFE_IMAGE_PROVIDER=openai`, but the
  account's credits ran out on 22 July 2026 and `gpt-image-1` answers `insufficient_quota`.
- Dead RSS feeds (moz.gov.ua, ukrinform, unian, medicalnewstoday) return 404 and are
  tolerated. Working ones: bbc_health, who_news.

## Content Focus

NOT breaking news. Focus on:
- Evidence-based research summaries
- Practical guides & lifehacks
- Healthy eating & nutrition
- Physical activity & fitness innovations
- Mental health & longevity
- Sleep, stress management, biohacking
