"""Stage 3b: Text editor - the craft pass between generation and the scientific gate.

Split out of the review because one mixed checklist let the model trade prose against
science and call both fine: a piece with clean sourcing scored well enough that a headline
hiding its own subject, or a paragraph of bare d-values, went out anyway. This pass owns
only how the piece reads - the headline, the four attention gates, the arc, numbers turned
into meaning, cadence - and touches no claim. The scientific gate runs after it, so the
science always has the last word on the text that actually ships.

Best-effort by design. Anything that comes back damaged - a dropped citation, a lost image,
a body that stops early - is discarded and the generated draft goes on unedited. A polish
step must never be able to destroy a good article.
"""

from __future__ import annotations

import logging
import re

from pipeline.config import AUTHOR_NAME, CONTENT_TYPES, MODEL_EDIT
from pipeline.context import PipelineContext
from pipeline.prompts.builder import build_text_editor_prompt
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query
from pipeline.stages.s3_generate import (
    normalize_dashes,
    strip_leading_metadata,
    strip_sources_section,
)

logger = logging.getLogger(__name__)

# How much of the draft has to survive. Editing tightens prose, and a padded draft can
# legitimately lose a fifth of its words, but a body that comes back at a third of its
# length is a truncated JSON string that happened to parse - the same failure s5_revise
# hits on long pieces - not an edit.
MIN_LENGTH_RATIO = 0.7

# How many change lines from the model reach the log. Enough to see what the pass did on a
# material, not so many that one stage owns the run log.
MAX_LOGGED_CHANGES = 12

_CITATION = re.compile(r"\[(\d{1,3})\]")
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
_INTERNAL_LINK = re.compile(r"(?<!\!)\[[^\]]+\]\((https?://[^)\s]*longlife\.media[^)\s]*)\)")


def run(ctx: PipelineContext) -> None:
    if not ctx.article_text:
        return

    type_cfg = CONTENT_TYPES.get(ctx.slot_type, CONTENT_TYPES["research"])
    system, prompt = build_text_editor_prompt(ctx, AUTHOR_NAME, type_cfg)

    # Same shape of failure as s5_revise: the whole body comes back as one JSON string, and
    # on a material that payload is big enough to truncate and take JSON repair with it. A
    # failed edit degrades to "no change this stage", never to a lost article.
    try:
        result = structured_query(
            prompt=prompt,
            system_prompt=system,
            schema=load_schema("text_edit"),
            model=MODEL_EDIT,
        )
    except Exception:
        logger.warning("Text edit failed; keeping the generated draft", exc_info=True)
        return

    edited = result.get("article") or ""
    if not edited.strip():
        logger.warning("Text edit returned an empty body; keeping the generated draft")
        return

    # A stage whose job includes killing the long dash still gets long dashes back, so count
    # them before normalising: that number is the honest measure of how hard the prompt is
    # having to fight the model here.
    reintroduced = edited.count("—")
    if reintroduced:
        logger.info("Text edit re-introduced %d long dash(es); normalised", reintroduced)

    # The editor's output needs the same cleanup as generation and revision: it re-introduces
    # the em-dash and now and then prefixes "Category:"/"Tags:" or re-appends a "Джерела"
    # list, and without this the polish quietly undoes what s3_generate cleaned.
    body = normalize_dashes(strip_sources_section(strip_leading_metadata(edited)))

    problems = _damage(ctx.article_text, body)
    if problems:
        logger.warning("Text edit rejected (%s); keeping the generated draft",
                       "; ".join(problems))
        return

    words_before = len(ctx.article_text.split())
    ctx.article_text = body

    # The headline is this pass's business, so a rewritten one is taken - but only when it is
    # actually there. An empty field means "left it alone", not "drop the title".
    title = normalize_dashes(result.get("title") or "").strip()
    if title:
        ctx.title = title
    description = normalize_dashes(result.get("description") or "").strip()
    if description:
        ctx.description = description

    for change in (result.get("changes") or [])[:MAX_LOGGED_CHANGES]:
        logger.info("Text edit: %s", str(change)[:160])
    logger.info("Text edit applied: %d words (was %d)",
                len(ctx.article_text.split()), words_before)


def _damage(original: str, edited: str) -> list[str]:
    """Everything that makes this edit worse than no edit.

    The editor is allowed to rewrite every sentence it likes, so there is nothing to diff the
    prose against. What is checked is the machinery a reader would notice broken: the
    citation numbers the page builds its "Джерела" list from, the inline illustrations, the
    links back to Vita's earlier posts, and whether the whole piece actually came back.
    """
    problems: list[str] = []

    before = set(_CITATION.findall(original))
    after = set(_CITATION.findall(edited))
    lost = sorted(before - after, key=int)
    gained = sorted(after - before, key=int)
    if lost:
        # A missing number is not cosmetic: the claim it carried is now unsourced on the page
        # while the numbered list below still counts it.
        problems.append("citations dropped: " + ", ".join(f"[{n}]" for n in lost))
    if gained:
        # A number with no entry in the source arrays renders as a citation to nothing.
        problems.append("citations invented: " + ", ".join(f"[{n}]" for n in gained))

    lost_images = set(_IMAGE.findall(original)) - set(_IMAGE.findall(edited))
    if lost_images:
        problems.append(f"{len(lost_images)} image line(s) dropped")

    lost_links = set(_INTERNAL_LINK.findall(original)) - set(_INTERNAL_LINK.findall(edited))
    if lost_links:
        problems.append(f"{len(lost_links)} longlife.media link(s) dropped")

    # normalize_dashes has already swapped every long dash for a spaced hyphen, so this fires
    # only if that ever stops being true. It is the invariant this stage promises, kept as a
    # check rather than an assumption - and cheap enough to leave standing.
    if "—" in edited:
        problems.append("long dash survived normalisation")

    words_before = len(original.split())
    words_after = len(edited.split())
    if words_before and words_after < words_before * MIN_LENGTH_RATIO:
        problems.append(f"body shrank {words_before} -> {words_after} words")

    return problems
