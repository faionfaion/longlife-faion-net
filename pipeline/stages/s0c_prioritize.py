"""Stage 0c: score the day's shortlist, keep one subject, file the rest.

The planner hands over eight to ten ideas every night and the blog writes one of them. Until
this stage existed, that one was whichever idea the model happened to list first — the
`priority` field in the plan was written by the planner and read by nobody — and the other
nine were thrown away at dawn, every day, including the good ones.

So this stage does two things. It scores every idea against the same fixed criteria (reader
value, whether the literature actually exists, whether something is happening around it,
whether we published it last week, and whether it has the substance to carry today's kind of
post) and returns them ranked, so the day's post is the best subject on the list rather than
the first one. And it writes everything below the cut into `state/backlog.json`, so an idea
that lost to a better idea comes back as a candidate tomorrow instead of evaporating.

Scoring is comparison against written-down criteria rather than creation or judgement, which
is why it runs on Sonnet while everything that writes stays on Opus.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from pipeline.config import CONTENT_TYPES, MODEL_PRIORITIZE, STATE_DIR
from pipeline.prompts.builder import build_prioritize_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query
from pipeline.stages import s0_editorial_plan

logger = logging.getLogger(__name__)

BACKLOG_FILE = STATE_DIR / "backlog.json"

# Health news ages. An idea that has sat unwritten for a month has usually been overtaken by
# its own field or by something the blog published in the meantime, and keeping it forever
# would slowly turn the backlog into a museum the planner has to read every night.
BACKLOG_TTL_DAYS = 30

# How many backlog entries the planner is shown. The file holds a month of losing ideas —
# a couple of hundred — and handing all of them over would cost more prompt than the whole
# rest of the planning context. The best-scoring dozen is a real second chance without that.
MAX_PLANNER_CANDIDATES = 12

# The plan's angles run to a thousand characters each; in the candidate list the planner only
# needs enough to recognise the idea and decide whether to promote it. The full text stays in
# the file, so a promoted idea keeps its whole brief.
_ANGLE_PREVIEW = 400
_SOURCES_PREVIEW = 200

# The prioritiser needs the recent articles to spot a repeat, not to read them. Trimming the
# stored summaries keeps this stage's prompt around a fifth of what the planner sends.
_RECENT_SUMMARY_PREVIEW = 220

# The fields the backlog carries forward, in the shape the editorial plan schema expects, so
# a promoted entry can go straight back into a plan without being rebuilt.
_BRIEF_FIELDS = ("type", "category", "angle", "sources_hint", "evidence_level")

# What a rank on the planner's own `priority` field is worth when the scoring call fails.
# Invented numbers, deliberately mid-range: they exist so a fallback day's ideas still
# compete for a place in tomorrow's candidate list instead of all landing at zero.
_PRIORITY_FALLBACK_SCORE = {1: 60, 2: 45, 3: 30}

_PUNCT = re.compile(r"[\s«»\"'“”„‘’—–\-:;,.!?()\[\]/]+")


def run(
    plan: dict,
    kind: str,
    limit: int = 1,
    recent_summaries: str | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """Rank today's shortlist and file everything under the cut.

    Returns the plan's articles best-first, each carrying `rank`, `score` and `rationale`.
    The caller walks that list and writes the top one; `limit` is where the cut falls, so a
    run with `--limit 3` backlogs from fourth place down rather than from second.
    """
    articles = plan.get("articles", [])
    if not articles:
        return []

    cut = max(limit or 1, 1)
    today_str = plan.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_of_week = _weekday_name(today_str)

    if recent_summaries is None:
        # The planner's own helper, so "recent" means the same thing in both stages: change
        # the window there and the duplication check here moves with it.
        recent_summaries = _compact_recent(s0_editorial_plan._load_recent_articles(days=30))

    ranked = _score(articles, kind, today_str, day_of_week, recent_summaries)

    # The whole ranking goes to the log, not just the winner: when a day's post turns out to
    # be the wrong subject, this is the record of what it beat and why.
    for item in ranked:
        logger.info("[prioritize] #%-2d %3d  %s  -- %s", item["rank"], item["score"],
                    item["topic"][:70], item.get("rationale", ""))

    logger.info("Prioritised %d topics; today's subject: %s",
                len(ranked), ranked[0]["topic"][:70])

    _record_backlog(ranked[cut:], today_str, dry_run=dry_run)
    return ranked


def load_backlog() -> list[dict]:
    """Live backlog entries, newest write order preserved. Missing or corrupt file reads empty."""
    if not BACKLOG_FILE.exists():
        return []
    try:
        data = json.loads(BACKLOG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Backlog file is not valid JSON, treating it as empty: %s", BACKLOG_FILE)
        return []
    entries = data.get("entries", []) if isinstance(data, dict) else data
    return [e for e in entries if isinstance(e, dict) and e.get("topic")]


def format_backlog_candidates(limit: int = MAX_PLANNER_CANDIDATES) -> str:
    """The best live backlog entries, formatted for the planner's candidate block.

    Sorted by score, newest first on a tie: the point is to put the strongest unwritten ideas
    back in front of the planner, and freshness breaks the tie because scores from different
    nights were set against different headlines.
    """
    entries = load_backlog()
    if not entries:
        return ""

    best = sorted(
        entries,
        key=lambda e: (_as_int(e.get("score")), e.get("proposed", "")),
        reverse=True,
    )[:limit]

    blocks = []
    for entry in best:
        blocks.append(
            f"- [{entry.get('proposed', '?')}, score {_as_int(entry.get('score'))}] "
            f"{entry.get('topic', '')}\n"
            f"  type: {entry.get('type', '?')} | category: {entry.get('category', '?')} | "
            f"expected evidence: {entry.get('evidence_level', '?')}\n"
            f"  angle: {_clip(entry.get('angle', ''), _ANGLE_PREVIEW)}\n"
            f"  sources: {_clip(entry.get('sources_hint', ''), _SOURCES_PREVIEW)}\n"
            f"  why it lost: {entry.get('rationale', '')}"
        )
    return "\n\n".join(blocks)


def drop_from_backlog(topic_label: str, dry_run: bool = False) -> None:
    """Remove an idea from the backlog once it has actually been written.

    Without this the backlog would keep offering the planner subjects the blog published a
    week ago, which is the exact mistake it exists to prevent.
    """
    if dry_run or not topic_label:
        return
    entries = load_backlog()
    key = _norm(topic_label)
    remaining = [e for e in entries if _norm(e.get("topic", "")) != key]
    if len(remaining) != len(entries):
        _save_backlog(remaining)
        logger.info("Backlog: dropped written topic (%d left)", len(remaining))


# ---- Scoring ----

def _score(
    articles: list[dict],
    kind: str,
    today_str: str,
    day_of_week: str,
    recent_summaries: str,
) -> list[dict]:
    """Ask the model for scores, then hang them back on the plan's own topic dicts."""
    system, prompt = build_prioritize_prompt(
        today_str=today_str,
        day_of_week=day_of_week,
        slot_brief=_slot_brief(kind),
        topics_text=_format_topics(articles),
        recent_summaries=recent_summaries,
    )

    try:
        result = structured_query(
            prompt=prompt,
            system_prompt=system,
            schema=load_schema("topic_ranking"),
            model=MODEL_PRIORITIZE,
        )
        scored = result.get("ranked") or []
    except Exception:
        logger.warning("Prioritiser failed, falling back to the planner's priority field",
                       exc_info=True)
        return _fallback_ranking(articles)

    merged = _merge(articles, scored)
    if merged is None:
        logger.warning("Prioritiser matched too few topics, falling back to the planner's "
                       "priority field")
        return _fallback_ranking(articles)
    return merged


def _merge(articles: list[dict], scored: list[dict]) -> list[dict] | None:
    """Attach scores to the article dicts and order them. None if the match was too poor.

    The model copies the topic line back, so most rows match on the label as written; the
    normalised and fuzzy passes catch the cases where it tidied a dash or a quotation mark on
    the way. An article nobody scored is kept rather than dropped — it goes to the tail and
    into the backlog, because an unscored idea is not the same thing as a rejected one.
    """
    by_norm = {_norm(a.get("topic", "")): a for a in articles}
    taken: dict[int, dict] = {}

    for row in scored:
        article = _match(row.get("topic", ""), articles, by_norm)
        if article is None or id(article) in taken:
            continue
        taken[id(article)] = {
            **article,
            "score": _as_int(row.get("score")),
            "rationale": (row.get("rationale") or "").strip(),
            "rank": _as_int(row.get("rank")),
        }

    if len(taken) * 2 < len(articles):
        return None

    ordered = sorted(
        taken.values(),
        key=lambda item: (-item["score"], item["rank"] or 99),
    )
    ordered.extend(
        {**a, "score": 0, "rationale": "left unscored by the prioritiser", "rank": 0}
        for a in articles if id(a) not in taken
    )

    # The model's own rank is a sanity signal we sort by; the number the rest of the pipeline
    # logs and stores is this one, so it is always 1..N with no gaps whatever came back.
    for position, item in enumerate(ordered, 1):
        item["rank"] = position
    return ordered


def _match(label: str, articles: list[dict], by_norm: dict[str, dict]) -> dict | None:
    key = _norm(label)
    if not key:
        return None
    if key in by_norm:
        return by_norm[key]
    close = difflib.get_close_matches(key, list(by_norm), n=1, cutoff=0.75)
    return by_norm[close[0]] if close else None


def _fallback_ranking(articles: list[dict]) -> list[dict]:
    """Order on the planner's own `priority` field — the thing this stage exists to replace.

    It is a poor ranking, which is why the stage exists at all, but it is a defined one and it
    keeps the night's post from becoming whatever the model listed first.
    """
    ordered = sorted(
        enumerate(articles),
        key=lambda pair: (_as_int(pair[1].get("priority")) or 3, pair[0]),
    )
    ranked = []
    for position, (_, article) in enumerate(ordered, 1):
        priority = _as_int(article.get("priority")) or 3
        ranked.append({
            **article,
            "score": _PRIORITY_FALLBACK_SCORE.get(priority, 30),
            "rationale": f"prioritiser unavailable; ordered by the planner's priority {priority}",
            "rank": position,
        })
    return ranked


# ---- Backlog ----

def _record_backlog(losers: list[dict], today_str: str, dry_run: bool) -> None:
    """Fold today's unwritten ideas into the backlog, newest score winning."""
    if not losers:
        return
    if dry_run:
        logger.info("Backlog: dry run, %d idea(s) not filed", len(losers))
        return

    entries = load_backlog()
    by_norm = {_norm(e.get("topic", "")): e for e in entries}
    added = 0

    for item in losers:
        entry = _entry(item, today_str)
        existing = by_norm.get(_norm(entry["topic"]))
        if existing is None:
            entries.append(entry)
            by_norm[_norm(entry["topic"])] = entry
            added += 1
        else:
            # The same idea proposed again: it keeps its place but takes today's score, today's
            # reasoning and today's date, so a subject that keeps coming back and keeps losing
            # does not age out while it is still being proposed.
            existing.update(entry)

    kept = _save_backlog(entries)
    logger.info("Backlog: %d new, %d refreshed, %d live", added, len(losers) - added, kept)


def _entry(item: dict, today_str: str) -> dict:
    entry = {"topic": item.get("topic", "")}
    entry.update({field: item.get(field, "") for field in _BRIEF_FIELDS})
    entry["score"] = _as_int(item.get("score"))
    entry["rationale"] = item.get("rationale", "")
    entry["proposed"] = today_str
    return entry


def _save_backlog(entries: list[dict]) -> int:
    """Write the backlog, dropping anything past its expiry. Returns how many survived."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=BACKLOG_TTL_DAYS)).strftime("%Y-%m-%d")
    live = [e for e in entries if (e.get("proposed") or "") >= cutoff]
    expired = len(entries) - len(live)

    BACKLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entries": live,
    }
    BACKLOG_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if expired:
        logger.info("Backlog: %d idea(s) expired after %d days", expired, BACKLOG_TTL_DAYS)
    return len(live)


# ---- Formatting helpers ----

def _slot_brief(kind: str) -> str:
    """What today's post has to be, in the terms the scoring criteria use."""
    cfg = CONTENT_TYPES.get(kind)
    if kind == "material" and cfg:
        return (
            f"Today is a material: one long feature of {cfg['min_words']}-{cfg['max_words']} "
            "words with room for history, current state and what to do. It needs a subject "
            "with enough substance to hold that length — a body of literature, a story with "
            "more than one turn, something to argue with. A single small study cannot carry it."
        )
    if kind == "roundup" and cfg:
        return (
            f"Today is the week's roundup: {cfg['min_words']}-{cfg['max_words']} words "
            "gathering several findings around one theme. It needs a subject broad enough "
            "that more than one piece of recent evidence belongs under it."
        )
    return (
        "Today is a normal post: one subject read properly and given a position, roughly "
        "400-2000 words depending on what kind of piece the idea itself calls for. It needs "
        "a subject that can be settled in one sitting rather than surveyed."
    )


def _format_topics(articles: list[dict]) -> str:
    blocks = []
    for i, article in enumerate(articles, 1):
        blocks.append(
            f"{i}. {article.get('topic', '')}\n"
            f"   type: {article.get('type', '?')} | category: {article.get('category', '?')} | "
            f"expected evidence: {article.get('evidence_level', '?')}\n"
            f"   angle: {article.get('angle', '')}\n"
            f"   sources hint: {article.get('sources_hint', '')}"
        )
    return "\n\n".join(blocks)


def _compact_recent(recent: str) -> str:
    """Trim the planner's recent-articles block down to what a duplication check needs.

    The stored summaries run to a thousand characters each and there can be eighty of them.
    The title, the date and the first couple of sentences are enough to recognise a repeat;
    the slug line is only there for the planner's cross-links.
    """
    lines = []
    for line in recent.split("\n"):
        if line.startswith("  Slug: "):
            continue
        if line.startswith("  Summary: "):
            line = _clip(line, len("  Summary: ") + _RECENT_SUMMARY_PREVIEW)
        lines.append(line)
    return "\n".join(lines)


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def _norm(label: str) -> str:
    """Topic labels as a dedupe key: case, spacing and punctuation are noise here."""
    return _PUNCT.sub(" ", label or "").casefold().strip()


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _weekday_name(today_str: str) -> str:
    try:
        return datetime.strptime(today_str, "%Y-%m-%d").strftime("%A")
    except ValueError:
        return datetime.now(timezone.utc).strftime("%A")
