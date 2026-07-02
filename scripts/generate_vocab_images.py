#!/usr/bin/env python3
"""Pre-generate vocabulary illustrations with OpenAI and cache them on disk.

Usage:
  cd backend && ../scripts/generate_vocab_images.py --weeks 1,2,3
  ../scripts/generate_vocab_images.py --level A1
  ../scripts/generate_vocab_images.py --all
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import os
import sys

import httpx
from PIL import Image

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from app.config import get_settings  # noqa: E402
from app.curriculum.program import WEEKS  # noqa: E402
from app.curriculum.a1_boost import A1_BOOST  # noqa: E402
from app.curriculum.a1_boost_extra import A1_BOOST_EXTRA  # noqa: E402
from app.vocab_images import (  # noqa: E402
    image_file_for,
    images_dir,
    invalidate_manifest_cache,
    save_manifest_entry,
    vocab_slug,
)

PROMPT = "Simple flat flashcard illustration: {gloss}. One clear subject, soft colors, plain background. No text."


def image_request_body(settings, prompt: str) -> dict:
    model = os.environ.get("OPENAI_IMAGE_MODEL") or settings.openai_image_model
    size = os.environ.get("OPENAI_IMAGE_SIZE") or settings.openai_image_size
    quality = os.environ.get("OPENAI_IMAGE_QUALITY") or settings.openai_image_quality
    body: dict = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    if model.startswith("gpt-image") or model.startswith("dall-e-3"):
        body["quality"] = quality
    if model.startswith("gpt-image"):
        body["output_format"] = "webp"
        body["output_compression"] = 80
    return body


def optimize_for_mobile(raw: bytes, settings) -> tuple[bytes, str]:
    """Downscale API output for small phone flashcards; keeps API quality, saves disk/bandwidth."""
    px = int(getattr(settings, "openai_image_save_px", 0) or 0)
    fmt = (getattr(settings, "openai_image_save_format", "webp") or "webp").lower()
    if px <= 0 and fmt == "png":
        return raw, "png"
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        if px > 0:
            img.thumbnail((px, px), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        if fmt == "webp":
            img.save(buf, format="WEBP", quality=82, method=4)
            return buf.getvalue(), "webp"
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "png"
    except Exception:
        return raw, "png"


def collect_vocab(
    weeks: list[int] | None,
    level: str | None,
    limit: int | None,
) -> list[tuple[str, str, str]]:
    seen: dict[str, tuple[str, str, str]] = {}
    for wk in WEEKS:
        if level is not None and wk.get("level") != level:
            continue
        if weeks is not None and wk["week"] not in weeks:
            continue
        for raw in wk.get("vocab", []):
            slug = vocab_slug(raw[0])
            seen[slug] = raw
        if wk.get("level") == "A1":
            w = wk["week"]
            for raw in A1_BOOST.get(w, []) + A1_BOOST_EXTRA.get(w, []):
                slug = vocab_slug(raw[0])
                seen.setdefault(slug, raw)
    out = list(seen.values())
    if limit:
        return out[:limit]
    return out


async def generate_one(client: httpx.AsyncClient, settings, es: str, en: str) -> bytes | None:
    gloss = en.split("(")[0].strip() or es
    prompt = PROMPT.format(gloss=gloss)
    url = f"{settings.openai_base_url}/images/generations"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = image_request_body(settings, prompt)
    resp = await client.post(url, headers=headers, json=body, timeout=90)
    if resp.status_code != 200:
        print(f"  FAIL {es}: HTTP {resp.status_code} {resp.text[:200]}")
        return None
    data = resp.json()["data"][0]
    if "url" in data:
        img = await client.get(data["url"], timeout=60)
        return img.content if img.status_code == 200 else None
    if "b64_json" in data:
        return base64.b64decode(data["b64_json"])
    return None


async def run(args):
    settings = get_settings()
    if not settings.openai_api_key:
        print("Set OPENAI_API_KEY in .env first.")
        sys.exit(1)

    words = collect_vocab(args.weeks, args.level, args.limit if not args.all else None)
    if args.all:
        words = collect_vocab(None, None, None)

    os.makedirs(images_dir(), exist_ok=True)
    todo = [(es, en, ru) for es, en, ru in words if not image_file_for(es)]
    print(f"Total unique words: {len(words)}, to generate: {len(todo)}", flush=True)

    async with httpx.AsyncClient() as client:
        for i, (es, en, ru) in enumerate(todo, start=1):
            slug = vocab_slug(es)
            print(f"[{i}/{len(todo)}] {es} …", flush=True)
            raw = await generate_one(client, settings, es, en)
            if not raw:
                continue
            raw, ext = optimize_for_mobile(raw, settings)
            fname = f"{slug}.{ext}"
            path = os.path.join(images_dir(), fname)
            with open(path, "wb") as fh:
                fh.write(raw)
            save_manifest_entry(slug, fname, es, en)
            invalidate_manifest_cache()
            await asyncio.sleep(0.2)

    print("Done.", flush=True)


def recompress_existing(settings):
    from app.vocab_images import _load_manifest, images_dir, save_manifest_entry, invalidate_manifest_cache

    manifest = _load_manifest()
    if not manifest:
        print("No manifest entries.", flush=True)
        return
    print(f"Recompressing {len(manifest)} images to {settings.openai_image_save_px}px {settings.openai_image_save_format}…", flush=True)
    for i, (slug, entry) in enumerate(manifest.items(), start=1):
        fname = entry.get("file") if isinstance(entry, dict) else entry
        if not fname:
            continue
        path = os.path.join(images_dir(), fname)
        if not os.path.isfile(path):
            print(f"  skip {slug}: missing file", flush=True)
            continue
        with open(path, "rb") as fh:
            raw = fh.read()
        out, ext = optimize_for_mobile(raw, settings)
        new_fname = f"{slug}.{ext}"
        new_path = os.path.join(images_dir(), new_fname)
        with open(new_path, "wb") as fh:
            fh.write(out)
        if new_fname != fname and os.path.isfile(path):
            os.remove(path)
        word_es = entry.get("es", slug) if isinstance(entry, dict) else slug
        gloss = entry.get("en", "") if isinstance(entry, dict) else ""
        save_manifest_entry(slug, new_fname, word_es, gloss)
        print(f"  [{i}/{len(manifest)}] {slug}: {len(raw)//1024}KB -> {len(out)//1024}KB", flush=True)
    invalidate_manifest_cache()
    print("Recompress done.", flush=True)


def parse_weeks(value: str | None) -> list[int] | None:
    if not value:
        return None
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(description="Generate cached vocab flashcard images")
    parser.add_argument("--weeks", type=str, default=None, help="Week numbers, e.g. 1,2,3")
    parser.add_argument("--level", type=str, default=None, help="Only words from this CEFR level (e.g. A1)")
    parser.add_argument("--limit", type=int, default=None, help="Max new images to generate")
    parser.add_argument("--all", action="store_true", help="All curriculum words (can be expensive)")
    parser.add_argument("--recompress", action="store_true", help="Resize existing cached images (no API calls)")
    args = parser.parse_args()
    args.weeks = parse_weeks(args.weeks)
    if args.recompress:
        recompress_existing(get_settings())
        return
    if not args.all and args.limit is None and args.weeks is None and args.level is None:
        args.weeks = [1, 2, 3]
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
