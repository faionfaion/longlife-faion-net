#!/usr/bin/env python3
"""Generate comic-style images for health articles using OpenAI gpt-image-1."""

import base64
import sys
import time
from pathlib import Path

import openai

client = openai.OpenAI()

STYLE = (
    "Clean-line comic art panel, bold black outlines, cel-shading, flat colors. "
    "Emerald green, warm gold, white, coral palette. No photo-realism."
)

CHARACTER = (
    "Vita — a tall athletic muscular blonde woman with long wavy hair past her shoulders "
    "(parted left), bright green eyes, a green leaf tattoo on her right shoulder, "
    "a fitness smartwatch on her left wrist. She wears a black sports bra, emerald green "
    "leggings, and white shoes"
)

IMAGES = [
    {
        "slug": "cold-shower-protocol-30-days",
        "prompt": (
            f"{STYLE} {CHARACTER}. "
            "Vita stands under a shower, reaching to turn the faucet to cold. "
            "Visible goosebumps on her skin. Her expression is fiercely determined. "
            "Water streams down. Blue cold-water particles and steam contrast. "
            "Bathroom tiles in the background."
        ),
    },
    {
        "slug": "desk-stretching-routine-5-min",
        "prompt": (
            f"{STYLE} {CHARACTER} (wearing a fitted emerald green long-sleeve top instead of sports bra). "
            "Vita demonstrates a neck stretch at an office desk — one hand gently pulls her head to the side. "
            "A computer monitor with green accent screen sits on the desk. Office chair, keyboard visible. "
            "Warm overhead lighting."
        ),
    },
    {
        "slug": "evening-routine-better-sleep-protocol",
        "prompt": (
            f"{STYLE} {CHARACTER} (wearing a cozy oversized warm gold hoodie and emerald green joggers). "
            "Vita sits in a comfortable armchair reading a book. A dim warm table lamp glows beside her. "
            "Her expression is sleepy and relaxed, eyes half-closed. "
            "Mug of herbal tea on a side table. Soft warm golden lighting throughout."
        ),
    },
    {
        "slug": "fall-asleep-10-minutes-military-technique",
        "prompt": (
            f"{STYLE} {CHARACTER} (wearing a simple white t-shirt and emerald green shorts). "
            "Vita lies on a military-style cot with her eyes closed, arms relaxed at her sides, "
            "completely at peace. A large analog countdown clock shows 10:00 on the wall. "
            "Minimalist military barracks setting. Calm blue-green atmosphere."
        ),
    },
    {
        "slug": "fermented-foods-homemade-probiotics-guide",
        "prompt": (
            f"{STYLE} {CHARACTER} (wearing a white apron over her default outfit). "
            "Vita stands in a bright kitchen, smiling, surrounded by glass jars of colorful "
            "fermented foods — pink kimchi, golden kombucha in a large jar with SCOBY visible, "
            "pale sauerkraut. She holds a jar proudly. Kitchen counter, cutting board, fresh "
            "vegetables in the background."
        ),
    },
    {
        "slug": "foam-rolling-guide-self-myofascial-release",
        "prompt": (
            f"{STYLE} {CHARACTER}. "
            "Vita uses a textured foam roller on her quadriceps on a gym floor. "
            "She supports herself with her arms, focused expression. "
            "Gym mat beneath her, dumbbells and exercise equipment subtly in background. "
            "Dynamic angle showing the rolling motion."
        ),
    },
    {
        "slug": "functional-training-vs-gym",
        "prompt": (
            f"{STYLE} {CHARACTER}. "
            "Vita performs a powerful kettlebell swing outdoors in a functional training area. "
            "She is mid-swing, hips thrust forward, kettlebell at chest height. "
            "Outdoor park setting with pull-up bars, ropes, tires in the background. "
            "Bright daylight, green grass, energetic pose."
        ),
    },
    {
        "slug": "gratitude-journaling-stress-response",
        "prompt": (
            f"{STYLE} {CHARACTER} (wearing an emerald green zip-up hoodie over her sports bra). "
            "Vita sits on a park bench writing in a small journal with a pen. "
            "Peaceful morning scene — trees with golden-green leaves, soft sunlight, "
            "a gentle smile on her face. A coffee cup sits beside her on the bench. "
            "Warm, serene atmosphere."
        ),
    },
]

OUT_DIR = Path("/home/nero/workspace/projects/longlife-faion-net/gatsby/static/images")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_image(slug: str, prompt: str) -> bool:
    """Generate a single image. Returns True on success."""
    out_path = OUT_DIR / f"{slug}.jpg"
    if out_path.exists():
        print(f"  SKIP {slug} (already exists)")
        return True

    print(f"  Generating {slug}...")
    try:
        resp = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1536x1024",
            n=1,
        )
        img_data = base64.b64decode(resp.data[0].b64_json)
        out_path.write_bytes(img_data)
        size_kb = len(img_data) / 1024
        print(f"  OK {slug} ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  FAIL {slug}: {e}", file=sys.stderr)
        return False


def main():
    print(f"Generating {len(IMAGES)} images to {OUT_DIR}/")
    success = 0
    failed = []
    for i, item in enumerate(IMAGES, 1):
        print(f"\n[{i}/{len(IMAGES)}] {item['slug']}")
        if generate_image(item["slug"], item["prompt"]):
            success += 1
        else:
            failed.append(item["slug"])
        # Small delay between API calls
        if i < len(IMAGES):
            time.sleep(2)

    print(f"\n{'=' * 40}")
    print(f"Done: {success}/{len(IMAGES)} images generated")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
