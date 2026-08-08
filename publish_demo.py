"""Publish the exact collagen demo shown to Ruslan — no regeneration.

Rebuilds the context from the saved article (so the text is byte-for-byte what he read),
then runs only the cover, teaser and save stages. Sources are pulled from the inline
citations in the body.
"""
import re
from pathlib import Path
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

from pipeline.context import PipelineContext
from pipeline.stages import s_comic_scene, s6_generate_tg, s7_save, s7_deploy

raw = Path("/tmp/claude-1000/-home-nero-workspace/a4560486-cfe3-4e81-8b27-9e8a1abbda28/scratchpad/debunk_article.md").read_text(encoding="utf-8")
body = raw.split("---\n\n", 1)[1].strip()

urls = re.findall(r"\((https?://[^)]+)\)", body)
seen, source_urls = set(), []
for u in urls:
    if u not in seen and "longlife.media" not in u:
        seen.add(u); source_urls.append(u)

ctx = PipelineContext()
ctx.slot_type = "post"
ctx.title = "Колаген у порошку для суглобів і шкіри: що насправді показують дослідження"
ctx.slug = "kolagen-poroshok-sugloby-shkira-shcho-kazhut-doslidzhennya"
ctx.article_text = body
ctx.description = ("Колаген продають на механізмі «будівельний матеріал». Для суглобів ефект "
                   "є, але дрібний; для шкіри зникає разом із грошима виробника.")
ctx.tags = ["колаген", "добавки", "суглоби", "остеоартроз", "шкіра", "доказова медицина"]
ctx.hashtags = "#колаген #добавки #суглоби #доказовамедицина"
ctx.source_urls = source_urls
ctx.source_names = []
ctx.summary = ("Claim-check колагенових добавок: мета-аналіз суглобів (35 РКД) дає малий "
               "ефект на біль (SMD −0.35); мета-аналіз шкіри показує, що ефект тримається "
               "лише в дослідженнях, оплачених виробниками.")

print("sources:", len(ctx.source_urls), "| words:", len(ctx.article_text.split()))

s_comic_scene.run(ctx)
s6_generate_tg.run(ctx)
s7_save.run(ctx)
s7_deploy.run()
print("SAVED:", ctx.slug, "| image:", ctx.image_path)
