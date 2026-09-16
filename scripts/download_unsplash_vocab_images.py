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
import re
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
    image_canonical_word,
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
    # Week 12 — first past tense (concrete photos, not icons/landmarks)
    "ayer": "person looking at old photograph remembering yesterday",
    "anoche": "night city lights mexico",
    "el fin de semana": "weekend family picnic park",
    "comí": "person eating tacos mexico",
    "comer": "person eating mexican food tacos",
    "fui": "person walking down street",
    "el cine": "cinema movie theater seats popcorn",
    "todo el día": "sunrise to sunset full day",
    "pasado": "old vintage photograph memory",
    "terminé": "student closing notebook after finishing homework",
    "terminar": "student closing notebook after finishing homework",
    "llegué": "person arriving home front door",
    "llegar": "person arriving train station",
    "vivir": "family living in house home",
    "escribir": "person writing letter notebook",
    "¿qué hiciste?": "two friends talking over coffee catching up",
    "qué hiciste": "two friends talking over coffee catching up",
    "qué hiciste ayer": "two friends talking over coffee catching up",
    "hacer": "person doing homework writing",
    "el día": "sunny day blue sky",
    "taco": "mexican tacos plate",
    "tacos": "mexican street tacos plate",
    "temprano": "early morning sunrise person waking coffee",
    "ayer por la mañana": "early morning sunrise beach walk",
    "ayer fui al cine": "people watching movie cinema seats popcorn",
    "no fui": "person staying home on sofa",
    "fue muy bueno": "people smiling applauding concert",
    "cuándo fue": "hand flipping calendar date page",
    "el pasado": "old black and white family photographs",
    "una vez": "hand showing one finger number one",
    "la semana pasada": "weekly planner previous week",
    "el mes pasado": "monthly calendar page turning",
    "el año pasado": "new year fireworks celebration night",
}

# Grammar labels / abstract tense names — skip photos rather than attach junk.
SKIP_IMAGE_KEYS = {
    "el pretérito",
    "el preterito",
    "la conjugación",
    "la conjugacion",
    "el verbo",
    "la forma",
    "terminación",
    "terminacion",
    "regular",
    "irregular",
}

_JUNK_PHOTO = re.compile(
    r"\b(3d|icon|illustration|render|logo|clipart|vector|mockup|thumbnail|"
    r"thumbs up|facebook|like button)\b",
    re.I,
)


def collect_vocab(weeks: list[int] | None, level: str | None, limit: int | None) -> list[tuple[str, str, str]]:
    seen: dict[str, tuple[str, str, str]] = {}
    for wk in WEEKS:
        if level is not None and wk.get("level") != level:
            continue
        if weeks is not None and wk["week"] not in weeks:
            continue
        for raw in wk.get("vocab", []):
            key = " ".join(raw[0].lower().replace("¿", "").replace("?", "").split())
            if key in SKIP_IMAGE_KEYS:
                continue
            seen[vocab_slug(raw[0])] = raw
        if wk.get("level") == "A1":
            w = wk["week"]
            for raw in A1_BOOST.get(w, []) + A1_BOOST_EXTRA.get(w, []):
                key = " ".join(raw[0].lower().replace("¿", "").replace("?", "").replace("…", "").split())
                if key in SKIP_IMAGE_KEYS:
                    continue
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


def photo_looks_like_photo(photo: dict) -> bool:
    blob = " ".join(
        filter(
            None,
            [
                photo.get("description"),
                photo.get("alt_description"),
                " ".join((t.get("title") or "") for t in (photo.get("tags") or [])),
            ],
        )
    )
    return not _JUNK_PHOTO.search(blob)


async def search_photo(client: httpx.AsyncClient, access_key: str, query: str, used_ids: set[str]) -> dict | None | str:
    """Return photo dict, None if empty, or 'rate_limited'."""
    resp = await client.get(
        "https://api.unsplash.com/search/photos",
        params={"query": query, "per_page": 10, "orientation": "squarish", "content_filter": "high"},
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
    for photo in results:
        pid = photo.get("id") or ""
        if pid and pid in used_ids:
            continue
        if not photo_looks_like_photo(photo):
            continue
        return photo
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
    if args.only:
        want = {vocab_slug(x) for x in args.only}
        words = [row for row in collect_vocab(None, None, None) if vocab_slug(row[0]) in want]
        if len(words) < len(want):
            # Allow downloading even if the lemma is not in the curriculum dump.
            have = {vocab_slug(row[0]) for row in words}
            for raw in args.only:
                if vocab_slug(raw) not in have:
                    words.append((raw, "", ""))
        args.force = True
    if args.limit:
        words = words[: args.limit]

    os.makedirs(images_dir(), exist_ok=True)
    # Conjugations share the infinitive image — download each lemma once.
    todo: list[tuple[str, str, str]] = []
    seen_keys: set[str] = set()
    for es, en, ru in words:
        skip_key = " ".join(es.lower().replace("¿", "").replace("?", "").replace("…", "").split())
        if skip_key in SKIP_IMAGE_KEYS:
            continue
        canonical = image_canonical_word(es)
        key = vocab_slug(canonical)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if not args.force and image_file_for(canonical):
            continue
        # Prefer infinitive row gloss when we collapsed a conjugated form.
        gloss_en, gloss_ru = en, ru
        if canonical != es:
            for ces, cen, cru in words:
                if vocab_slug(ces) == key:
                    gloss_en, gloss_ru = cen, cru
                    break
        todo.append((canonical, gloss_en, gloss_ru))

    print(f"Total unique words: {len(words)}, to download: {len(todo)}", flush=True)
    ok = 0
    fail = 0
    used_ids: set[str] = set()

    async with httpx.AsyncClient() as client:
        for i, (es, en, ru) in enumerate(todo, start=1):
            slug = vocab_slug(es)
            query = search_query(es, en)
            print(f"[{i}/{len(todo)}] {es} ← “{query}” …", flush=True)
            photo = await search_photo(client, access_key, query, used_ids)
            if photo == "rate_limited":
                print("Rate limit hit — stop and re-run later (demo apps ~50 req/hour).", flush=True)
                break
            if not photo:
                fallback = (en or es).split("(")[0].strip()
                if fallback and fallback != query:
                    print(f"  retry “{fallback}” …", flush=True)
                    photo = await search_photo(client, access_key, fallback, used_ids)
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
            if photo.get("id"):
                used_ids.add(photo["id"])
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
    parser.add_argument("--only", type=str, default=None, help="Comma-separated Spanish words or slugs to (re)download")
    parser.add_argument("--delay", type=float, default=1.2, help="Seconds between API calls")
    args = parser.parse_args()
    args.weeks = parse_weeks(args.weeks)
    args.only = [x.strip() for x in args.only.split(",") if x.strip()] if args.only else None
    if not args.all and args.limit is None and args.weeks is None and args.level is None and not args.only:
        args.weeks = [3]
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
