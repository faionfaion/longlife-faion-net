# LongLife Media — Healthy Lifestyle for Ukrainians

Evidence-based health media in Ukrainian. Site: longlife.faion.net, TG: @long_life_media.

## Structure

| Path | Purpose |
|------|---------|
| `pipeline/` | Publishing pipeline (Python, 3 modes: generate/publish/digest) |
| `pipeline/stages/` | Pipeline stages (s0-s11) |
| `gatsby/` | Static site (Gatsby 5 + React) |
| `content/` | Markdown articles (Ukrainian) |
| `scripts/` | Cron runner, utilities |
| `state/` | Runtime state (plans, teasers, posted, logs) |
| `admin/` | Flask admin panel |

## Pipeline Modes

| Mode | Cron | What |
|------|------|------|
| `generate` | `0 7 * * *` | Morning batch: editorial plan, all 8-10 articles, 1 deploy |
| `publish` | `5 9,12,15,18 * * *` | Mechanical: pick pre-generated article, send to TG (no LLM) |
| `digest` | `5 20 * * *` | Compile day's articles into evening digest to TG |

## Key Commands

```bash
python3 -m pipeline generate -v       # Batch generate all articles
python3 -m pipeline publish -v        # Mechanical TG publish
python3 -m pipeline digest -v         # Evening digest
python3 -m pipeline generate --dry-run  # Test without deploy
```

## Quick Reference

- **Bot:** @nero_open_bot (shared)
- **Channel:** @long_life_media
- **Domain:** longlife.faion.net (Cloudflare DNS -> faion-net nginx)
- **LLM:** All stages use Claude Opus via Agent SDK
- **Images:** OpenAI gpt-image-1, illustration style

## Content Focus

NOT breaking news. Focus on:
- Evidence-based research summaries
- Practical guides & lifehacks
- Healthy eating & nutrition
- Physical activity & fitness innovations
- Mental health & longevity
- Sleep, stress management, biohacking
