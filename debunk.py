"""Demo: a claim-check post in the new register (research stage, real sources)."""
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

from pipeline.context import PipelineContext
from pipeline.stages import s2_research, s3_generate

ctx = PipelineContext()
ctx.slot_type = "post"
ctx.posted_slugs = []
ctx.editorial_plan = {
    "topic": "Колаген у порошку для суглобів і шкіри: що насправді показують дослідження",
    "angle": "Класичний claim-check: продукт продають усюди на механізмі («колаген — це "
             "будівельний матеріал»), але з'їдений колаген розщеплюється до амінокислот. "
             "Пояснити простими словами, що кажуть РКД і мета-аналізи про суглобовий біль і "
             "шкіру, де ефект реальний, а де — маркетинг, і що це означає для звичайної людини.",
    "type": "post",
    "category": "nutrition",
    "sources_hint": "PubMed collagen peptides osteoarthritis RCT, collagen supplementation "
                    "skin elasticity meta-analysis, Cochrane, hydrolyzed collagen joint pain",
    "evidence_level": "moderate",
}

s2_research.run(ctx)
s3_generate.run(ctx)

print(f"\n=== {ctx.title} ===")
print(f"slug: {ctx.slug} | {len(ctx.article_text.split())} words | {len(ctx.source_urls)} sources\n")
print(ctx.article_text)

from pathlib import Path
out = Path("/tmp/claude-1000/-home-nero-workspace/a4560486-cfe3-4e81-8b27-9e8a1abbda28/scratchpad/debunk_article.md")
out.write_text(f"# {ctx.title}\n\nslug: {ctx.slug} | {len(ctx.article_text.split())} words | {len(ctx.source_urls)} sources\n\n---\n\n{ctx.article_text}\n", encoding="utf-8")
