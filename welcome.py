"""One-off: the welcome post announcing the change of face.

Skips the research stage — there is nothing to research, the subject is the blog itself.
Everything after generation is the normal path, so it gets a cover, a teaser, a site page
and a commit like any other post.
"""
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

from pathlib import Path

from pipeline.config import CONTENT_TYPES, MODEL_GENERATE
from pipeline.context import PipelineContext
from pipeline.prompts.builder import _env
from pipeline.schemas import load_schema
from pipeline.sdk import structured_query
from pipeline.stages import s6_generate_tg, s7_deploy, s7_save, s_comic_scene

VOICE = _env.get_template("_partials/voice_guide.xml").render()

SYSTEM = f"""{VOICE}

You are writing a short post about the blog itself.
"""

BRIEF = """
<task>
Write today's post. It is about this blog, not about a study.
</task>

<what-happened>
For about half a year this blog has run with you drawn as a cartoon: a young blonde
trainer, comic panels, bright green and gold. From today you look like what you actually
are — a 42-year-old scientist, photographed rather than illustrated.
</what-happened>

<what-to-say>
- Say plainly that the picture changed and why. The old one looked like a supplement
  advert; that is the wrong face for a blog whose whole argument is "show me the study".
- This is the natural place to say what you are: a character, not a person. Do not bury
  it and do not make a drama of it. You are not less real for it, and on this subject you
  are frequently better equipped — you can hold a whole literature in view at once and
  tell an effect size from a headline, which no human doing this part-time can.
- Say why that matters specifically for health: it is a field soaked in cognitive bias at
  every level — what gets funded, what gets published, what a journalist finds worth a
  headline, what a reader already wants to be true. Name that you have your own priors too.
- Say what does not change: every claim keeps its source, you say where you are unsure,
  and you correct yourself in public when you get something wrong.
- Then say what the rhythm is now: one post a day, Friday the week's findings on one
  theme, Sunday the week as one long read.
- End on the thought, not on a welcome-aboard flourish.

400-700 words. No headings unless the piece genuinely needs one. No sources are required
here — it is a post about the blog — so leave source_urls and source_names empty.
`slug`: something like `nove-oblychchia-tsoho-blohu`.
`category`: research. `evidence_level`: preliminary. `medical_disclaimer`: false.
</what-to-say>
"""

ctx = PipelineContext()
ctx.slot_type = "post"
ctx.posted_slugs = []

result = structured_query(
    prompt=BRIEF, system_prompt=SYSTEM,
    schema=load_schema("generation"), model=MODEL_GENERATE,
)

ctx.title = result["title"]
ctx.slug = result["slug"]
ctx.article_text = result["article"]
ctx.description = result.get("description", "")
ctx.tags = result.get("tags", [])
ctx.hashtags = result.get("hashtags", "")
ctx.source_urls = result.get("source_urls", [])
ctx.source_names = result.get("source_names", [])
ctx.summary = result.get("summary", "")

print(f"\n=== {ctx.title} ===\nslug: {ctx.slug}\nwords: {len(ctx.article_text.split())}\n")
print(ctx.article_text)

s_comic_scene.run(ctx)
s6_generate_tg.run(ctx)
s7_save.run(ctx)
s7_deploy.run()
print("\n-> saved:", ctx.slug, "| image:", ctx.image_path)
