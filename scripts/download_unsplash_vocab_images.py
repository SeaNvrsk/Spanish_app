#!/usr/bin/env python3
"""Download vocabulary flashcard photos from Unsplash and cache them on disk.

Usage:
  cd backend && ../scripts/download_unsplash_vocab_images.py --weeks 3
  ../scripts/download_unsplash_vocab_images.py --weeks 3 --limit 10
  ../scripts/download_unsplash_vocab_images.py --weeks 3 --force

Requires UNSPLASH_ACCESS_KEY in project .env.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
import time

import httpx
from PIL import Image

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from app.config import get_settings  # noqa: E402
from app.curriculum.a1_boost import A1_BOOST  # noqa: E402
from app.curriculum.a1_boost_extra import A1_BOOST_EXTRA  # noqa: E402
from app.curriculum.program import WEEKS  # noqa: E402
from app.vocab_images import (  # noqa: E402
    image_file_for,
    images_dir,
    invalidate_manifest_cache,
    save_manifest_entry,
    vocab_slug,
)

# Abstract / grammar words need a concrete photo query, not the Spanish lemma alone.
QUERY_OVERRIDES: dict[str, str] = {
    "soy": "person pointing to self portrait",
    "eres": "two people talking casually",
    "es": "person standing alone portrait",
    "somos": "group of friends together",
    "son": "group of people standing",
    "estoy": "person at home living room",
    "estás": "person looking at camera",
    "está": "person sitting cafe",
    "estamos": "family together outdoors",
    "están": "people waiting outdoors",
    "aquí": "here location pin map",
    "allá": "distant landscape horizon",
    "cansado": "tired person yawning",
    "feliz": "happy smiling person",
    "de méxico": "mexico city flag",
    "quién": "curious person asking question",
    "dónde": "map location search",
    "bien": "thumbs up ok gesture",
    "mal": "thumbs down unhappy",
    "muy": "very large emphasis arrow",
    "también": "also plus sign people",
    "pero": "but contrast fork road",
    "ser": "identity passport photo",
    "estar": "location place pin",
    "sois": "group of friends spain",
    "estáis": "people standing together",
    "bueno": "good thumbs up green",
    "buena": "good positive smile woman",
    "malo": "bad warning red",
    "mala": "bad unhappy expression",
    "alto": "tall person standing",
    "alta": "tall woman standing",
    "bajo": "short person standing",
    "baja": "short woman standing",
    "triste": "sad person crying",
    "enfermo": "sick person in bed",
    "enferma": "sick woman resting",
    "ocupado": "busy person working laptop",
    "ocupada": "busy woman working office",
    "abierto": "open door entrance",
    "cerrado": "closed door locked",
    "de": "from of preposition abstract",
    "en": "in on location indoors",
    "méxico": "mexico city landmark",
    "español": "spanish language spain flag",
    "mexicano": "mexican man portrait",
    "mexicana": "mexican woman portrait",
    "profesor": "male teacher classroom",
    "profesora": "female teacher classroom",
    "estudiante": "student studying books",
    "amable": "kind person helping",
    "inteligente": "smart student thinking",
    "de dónde eres": "where are you from passport travel",
    "soy de": "i am from hometown map",
    "estoy en la casa": "person at home living room",
    "está cerrado": "closed shop sign door",
    "son las tres": "clock three oclock",
    "es importante": "important priority checklist",
    "estoy contento": "happy content person smile",
    "cómo es": "what is it like description",
    "cómo estás hoy": "how are you today greeting",
    "serio": "serious man face",
    "seria": "serious woman face",
    "joven": "young person teenager",
    "mayor": "older elderly person",
    "listo": "ready person packing bag",
    "lista": "ready woman packing",
    "importante": "important document stamp",
    "posible": "possible opportunity door open",
    "imposible": "impossible blocked road",
    "normal": "normal everyday street",
    "raro": "weird unusual object",
    "diferente": "different colorful contrast",
    # Week 4 — family
    "la mamá": "mother mom portrait",
    "el papá": "father dad portrait",
    "el hermano": "brother young man",
    "la hermana": "sister young woman",
    "el hijo": "son boy child",
    "la hija": "daughter girl child",
    "el abuelo": "grandfather elderly man",
    "la abuela": "grandmother elderly woman",
    "el tío": "uncle smiling man",
    "la tía": "aunt smiling woman",
    "el esposo": "husband wedding man",
    "la esposa": "wife wedding woman",
    "los padres": "parents with children",
    "el bebé": "baby infant cute",
    "mi": "my hands holding heart",
    "su": "his her belongings",
    "nuestro": "our family together",
    "nuestra": "our family mother children",
    "la familia": "happy family together",
    "el niño": "little boy child",
    "la niña": "little girl child",
    "grande": "big large object",
    "pequeño": "small tiny object",
    "el padre": "father dad portrait",
    "la madre": "mother mom portrait",
    "el primo": "cousin young man",
    "la prima": "cousin young woman",
    "cuántos hermanos tienes": "siblings brothers sisters family",
    "mi familia es grande": "big family group photo",
    "es mi madre": "mother and child",
    "tengo dos hijos": "father with two children",
    "tienes hijos": "parent with children question",
    "vivo con mi familia": "family living at home",
    "el nieto": "grandson with grandparents",
    "la nieta": "granddaughter with grandparents",
    "los abuelos": "grandparents elderly couple",
    "menor": "younger sibling child",
    "solo": "alone person solitary",
    "casado": "married man wedding ring",
    "casada": "married woman wedding ring",
    "soltero": "single man alone",
    "soltera": "single woman alone",
    "estás casado": "wedding rings marriage",
    "el novio": "boyfriend young man",
    "la novia": "girlfriend young woman",
    "el vecino": "neighbor man house",
    "la vecina": "neighbor woman house",
    "el pariente": "family relatives gathering",
    "la gente": "crowd people street",
    "el hombre": "man portrait adult",
    "la mujer": "woman portrait adult",
}


def collect_vocab(weeks: list[int] | None, level: str | None, limit: int | None) -> list[tuple[str, str, str]]:
    seen: dict[str, tuple[str, str, str]] = {}
    for wk in WEEKS:
        if level is not None and wk.get("level") != level:
            continue
        if weeks is not None and wk["week"] not in weeks:
            continue
        for raw in wk.get("vocab", []):
            seen[vocab_slug(raw[0])] = raw
        if wk.get("level") == "A1":
            w = wk["week"]
            for raw in A1_BOOST.get(w, []) + A1_BOOST_EXTRA.get(w, []):
                seen.setdefault(vocab_slug(raw[0]), raw)
    out = list(seen.values())
    if limit:
        return out[:limit]
    return out


def search_query(es: str, en: str) -> str:
    key = " ".join(es.lower().replace("¿", "").replace("?", "").replace("…", "").split())
    if key in QUERY_OVERRIDES:
        return QUERY_OVERRIDES[key]
    gloss = (en or "").split("(")[0].strip()
    gloss = gloss.replace("...", "").strip(" .")
    if gloss and gloss.lower() not in {"to be", "i am", "you are", "he/she is"}:
        return f"{gloss} mexico"
    return f"{es} mexico"


def optimize_for_mobile(raw: bytes, settings) -> tuple[bytes, str]:
    px = int(getattr(settings, "openai_image_save_px", 0) or 512)
    fmt = (getattr(settings, "openai_image_save_format", "webp") or "webp").lower()
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
        return raw, "jpg"


async def search_photo(client: httpx.AsyncClient, access_key: str, query: str) -> dict | None | str:
    """Return photo dict, None if empty, or 'rate_limited'."""
    resp = await client.get(
        "https://api.unsplash.com/search/photos",
        params={"query": query, "per_page": 5, "orientation": "squarish", "content_filter": "high"},
        headers={"Authorization": f"Client-ID {access_key}", "Accept-Version": "v1"},
        timeout=30,
    )
    remaining = resp.headers.get("X-Ratelimit-Remaining")
    if remaining is not None:
        print(f"  (rate remaining={remaining})", flush=True)
    if resp.status_code == 403 and "Rate Limit" in (resp.text or ""):
        return "rate_limited"
    if resp.status_code == 403:
        print(f"  FAIL permission: {resp.text[:180]}")
        return None
    if resp.status_code != 200:
        print(f"  FAIL search HTTP {resp.status_code}: {resp.text[:180]}")
        return None
    results = resp.json().get("results") or []
    return results[0] if results else None


async def download_photo(client: httpx.AsyncClient, access_key: str, photo: dict) -> bytes | None:
    urls = photo.get("urls") or {}
    img_url = urls.get("small") or urls.get("regular") or urls.get("raw")
    if not img_url:
        return None
    # Prefer a square-ish crop around 512–800px
    if "?" in img_url:
        img_url = f"{img_url}&w=800&h=800&fit=crop"
    else:
        img_url = f"{img_url}?w=800&h=800&fit=crop"
    resp = await client.get(img_url, timeout=60, follow_redirects=True)
    if resp.status_code != 200:
        print(f"  FAIL download HTTP {resp.status_code}")
        return None
    # Trigger Unsplash download endpoint (required by API guidelines)
    download_loc = (photo.get("links") or {}).get("download_location")
    if download_loc:
        await client.get(
            download_loc,
            headers={"Authorization": f"Client-ID {access_key}", "Accept-Version": "v1"},
            timeout=20,
        )
    return resp.content


async def run(args):
    settings = get_settings()
    access_key = (settings.unsplash_access_key or os.environ.get("UNSPLASH_ACCESS_KEY") or "").strip()
    if not access_key:
        print("Set UNSPLASH_ACCESS_KEY in .env first.")
        sys.exit(1)

    words = collect_vocab(args.weeks, args.level, None)
    if args.all:
        words = collect_vocab(None, None, None)
    if args.limit:
        words = words[: args.limit]

    os.makedirs(images_dir(), exist_ok=True)
    if args.force:
        todo = list(words)
    else:
        todo = [(es, en, ru) for es, en, ru in words if not image_file_for(es)]

    print(f"Total unique words: {len(words)}, to download: {len(todo)}", flush=True)
    ok = 0
    fail = 0

    async with httpx.AsyncClient() as client:
        for i, (es, en, ru) in enumerate(todo, start=1):
            slug = vocab_slug(es)
            query = search_query(es, en)
            print(f"[{i}/{len(todo)}] {es} ← “{query}” …", flush=True)
            photo = await search_photo(client, access_key, query)
            if photo == "rate_limited":
                print("Rate limit hit — stop and re-run later (demo apps ~50 req/hour).", flush=True)
                break
            if not photo:
                fallback = (en or es).split("(")[0].strip()
                if fallback and fallback != query:
                    print(f"  retry “{fallback}” …", flush=True)
                    photo = await search_photo(client, access_key, fallback)
                    if photo == "rate_limited":
                        print("Rate limit hit — stop and re-run later.", flush=True)
                        break
            if not photo:
                fail += 1
                print(f"  MISS {es}")
                await asyncio.sleep(0.4)
                continue
            raw = await download_photo(client, access_key, photo)
            if not raw:
                fail += 1
                continue
            raw, ext = optimize_for_mobile(raw, settings)
            fname = f"{slug}.{ext}"
            path = os.path.join(images_dir(), fname)
            with open(path, "wb") as fh:
                fh.write(raw)
            save_manifest_entry(slug, fname, es, en)
            invalidate_manifest_cache()
            ok += 1
            photographer = ((photo.get("user") or {}).get("name")) or "?"
            print(f"  OK {fname} ({len(raw)//1024}KB) — {photographer}")
            await asyncio.sleep(args.delay)

    print(f"Done. ok={ok} fail={fail} remaining_without_image={sum(1 for es,_,_ in todo if not image_file_for(es))}", flush=True)


def parse_weeks(value: str | None) -> list[int] | None:
    if not value:
        return None
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(description="Download Unsplash photos for vocab flashcards")
    parser.add_argument("--weeks", type=str, default=None, help="Week numbers, e.g. 3 or 1,2,3")
    parser.add_argument("--level", type=str, default=None, help="Only words from this CEFR level")
    parser.add_argument("--limit", type=int, default=None, help="Max words to process")
    parser.add_argument("--all", action="store_true", help="All curriculum words")
    parser.add_argument("--force", action="store_true", help="Re-download even if image exists")
    parser.add_argument("--delay", type=float, default=1.2, help="Seconds between API calls")
    args = parser.parse_args()
    args.weeks = parse_weeks(args.weeks)
    if not args.all and args.limit is None and args.weeks is None and args.level is None:
        args.weeks = [3]
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
