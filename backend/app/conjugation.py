"""Spanish verb conjugation (Mexican usage — no vosotros)."""

import unicodedata

PRONOUNS = ("yo", "tú", "él/ella/usted", "nosotros", "ustedes", "ellos/ellas")

TENSES = ("present", "preterite", "imperfect", "future")

# Full paradigms: 6 forms matching PRONOUNS order.
IRREGULAR = {
    "ser": {
        "present": ["soy", "eres", "es", "somos", "son", "son"],
        "preterite": ["fui", "fuiste", "fue", "fuimos", "fueron", "fueron"],
        "imperfect": ["era", "eras", "era", "éramos", "eran", "eran"],
        "future": ["seré", "serás", "será", "seremos", "serán", "serán"],
    },
    "estar": {
        "present": ["estoy", "estás", "está", "estamos", "están", "están"],
        "preterite": ["estuve", "estuviste", "estuvo", "estuvimos", "estuvieron", "estuvieron"],
        "imperfect": ["estaba", "estabas", "estaba", "estábamos", "estaban", "estaban"],
        "future": ["estaré", "estarás", "estará", "estaremos", "estarán", "estarán"],
    },
    "ir": {
        "present": ["voy", "vas", "va", "vamos", "van", "van"],
        "preterite": ["fui", "fuiste", "fue", "fuimos", "fueron", "fueron"],
        "imperfect": ["iba", "ibas", "iba", "íbamos", "iban", "iban"],
        "future": ["iré", "irás", "irá", "iremos", "irán", "irán"],
    },
    "tener": {
        "present": ["tengo", "tienes", "tiene", "tenemos", "tienen", "tienen"],
        "preterite": ["tuve", "tuviste", "tuvo", "tuvimos", "tuvieron", "tuvieron"],
        "imperfect": ["tenía", "tenías", "tenía", "teníamos", "tenían", "tenían"],
        "future": ["tendré", "tendrás", "tendrá", "tendremos", "tendrán", "tendrán"],
    },
    "hacer": {
        "present": ["hago", "haces", "hace", "hacemos", "hacen", "hacen"],
        "preterite": ["hice", "hiciste", "hizo", "hicimos", "hicieron", "hicieron"],
        "imperfect": ["hacía", "hacías", "hacía", "hacíamos", "hacían", "hacían"],
        "future": ["haré", "harás", "hará", "haremos", "harán", "harán"],
    },
    "poder": {
        "present": ["puedo", "puedes", "puede", "podemos", "pueden", "pueden"],
        "preterite": ["pude", "pudiste", "pudo", "pudimos", "pudieron", "pudieron"],
        "imperfect": ["podía", "podías", "podía", "podíamos", "podían", "podían"],
        "future": ["podré", "podrás", "podrá", "podremos", "podrán", "podrán"],
    },
    "querer": {
        "present": ["quiero", "quieres", "quiere", "queremos", "quieren", "quieren"],
        "preterite": ["quise", "quisiste", "quiso", "quisimos", "quisieron", "quisieron"],
        "imperfect": ["quería", "querías", "quería", "queríamos", "querían", "querían"],
        "future": ["querré", "querrás", "querrá", "querremos", "querrán", "querrán"],
    },
    "decir": {
        "present": ["digo", "dices", "dice", "decimos", "dicen", "dicen"],
        "preterite": ["dije", "dijiste", "dijo", "dijimos", "dijeron", "dijeron"],
        "imperfect": ["decía", "decías", "decía", "decíamos", "decían", "decían"],
        "future": ["diré", "dirás", "dirá", "diremos", "dirán", "dirán"],
    },
    "venir": {
        "present": ["vengo", "vienes", "viene", "venimos", "vienen", "vienen"],
        "preterite": ["vine", "viniste", "vino", "vinimos", "vinieron", "vinieron"],
        "imperfect": ["venía", "venías", "venía", "veníamos", "venían", "venían"],
        "future": ["vendré", "vendrás", "vendrá", "vendremos", "vendrán", "vendrán"],
    },
    "poner": {
        "present": ["pongo", "pones", "pone", "ponemos", "ponen", "ponen"],
        "preterite": ["puse", "pusiste", "puso", "pusimos", "pusieron", "pusieron"],
        "imperfect": ["ponía", "ponías", "ponía", "poníamos", "ponían", "ponían"],
        "future": ["pondré", "pondrás", "pondrá", "pondremos", "pondrán", "pondrán"],
    },
    "saber": {
        "present": ["sé", "sabes", "sabe", "sabemos", "saben", "saben"],
        "preterite": ["supe", "supiste", "supo", "supimos", "supieron", "supieron"],
        "imperfect": ["sabía", "sabías", "sabía", "sabíamos", "sabían", "sabían"],
        "future": ["sabré", "sabrás", "sabrá", "sabremos", "sabrán", "sabrán"],
    },
    "haber": {
        "present": ["he", "has", "ha", "hemos", "han", "han"],
        "preterite": ["hube", "hubiste", "hubo", "hubimos", "hubieron", "hubieron"],
        "imperfect": ["había", "habías", "había", "habíamos", "habían", "habían"],
        "future": ["habré", "habrás", "habrá", "habremos", "habrán", "habrán"],
    },
    "dar": {
        "present": ["doy", "das", "da", "damos", "dan", "dan"],
        "preterite": ["di", "diste", "dio", "dimos", "dieron", "dieron"],
        "imperfect": ["daba", "dabas", "daba", "dábamos", "daban", "daban"],
        "future": ["daré", "darás", "dará", "daremos", "darán", "darán"],
    },
    "ver": {
        "present": ["veo", "ves", "ve", "vemos", "ven", "ven"],
        "preterite": ["vi", "viste", "vio", "vimos", "vieron", "vieron"],
        "imperfect": ["veía", "veías", "veía", "veíamos", "veían", "veían"],
        "future": ["veré", "verás", "verá", "veremos", "verán", "verán"],
    },
    "salir": {
        "present": ["salgo", "sales", "sale", "salimos", "salen", "salen"],
        "preterite": ["salí", "saliste", "salió", "salimos", "salieron", "salieron"],
        "imperfect": ["salía", "salías", "salía", "salíamos", "salían", "salían"],
        "future": ["saldré", "saldrás", "saldrá", "saldremos", "saldrán", "saldrán"],
    },
}

# Present stem-changing (e→ie, o→ue, e→i): stem for yo..ellos after change applied to stem.
STEM_CHANGE_PRESENT = {
    "pensar": ("e", "ie", ["pienso", "piensas", "piensa", "pensamos", "piensan", "piensan"]),
    "entender": ("e", "ie", ["entiendo", "entiendes", "entiende", "entendemos", "entienden", "entienden"]),
    "preferir": ("e", "ie", ["prefiero", "prefieres", "prefiere", "preferimos", "prefieren", "prefieren"]),
    "querer": None,  # in IRREGULAR
    "poder": None,
    "dormir": ("o", "ue", ["duermo", "duermes", "duerme", "dormimos", "duermen", "duermen"]),
    "volver": ("o", "ue", ["vuelvo", "vuelves", "vuelve", "volvemos", "vuelven", "vuelven"]),
    "pedir": ("e", "i", ["pido", "pides", "pide", "pedimos", "piden", "piden"]),
    "servir": ("e", "i", ["sirvo", "sirves", "sirve", "servimos", "sirven", "sirven"]),
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower().strip())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _strip_reflexive(verb: str) -> tuple[str, bool]:
    if verb.endswith("se") and len(verb) > 3:
        return verb[:-2], True
    return verb, False


def _regular_present(stem: str, ending: str) -> list[str]:
    if ending == "ar":
        return [stem + s for s in ("o", "as", "a", "amos", "an", "an")]
    if ending in ("er", "ir"):
        return [stem + s for s in ("o", "es", "e", "emos" if ending == "er" else "imos", "en", "en")]
    raise ValueError("invalid ending")


def _regular_preterite(stem: str, ending: str) -> list[str]:
    if ending == "ar":
        return [stem + s for s in ("é", "aste", "ó", "amos", "aron", "aron")]
    return [stem + s for s in ("í", "iste", "ió", "imos", "ieron", "ieron")]


def _regular_imperfect(stem: str, ending: str) -> list[str]:
    if ending == "ar":
        return [stem + s for s in ("aba", "abas", "aba", "ábamos", "aban", "aban")]
    return [stem + s for s in ("ía", "ías", "ía", "íamos", "ían", "ían")]


def _regular_future(infinitive: str) -> list[str]:
    return [infinitive + s for s in ("é", "ás", "á", "emos", "án", "án")]


def conjugate(verb: str, tense: str = "present") -> dict:
    """Return conjugation table for a verb. Raises ValueError if unknown."""
    raw = verb.strip()
    if not raw:
        raise ValueError("empty verb")
    tense = tense.lower().strip()
    if tense not in TENSES:
        raise ValueError(f"unsupported tense: {tense}")

    base, reflexive = _strip_reflexive(_norm(raw))
    if base.endswith("ar"):
        ending, stem = "ar", base[:-2]
    elif base.endswith("er"):
        ending, stem = "er", base[:-2]
    elif base.endswith("ir"):
        ending, stem = "ir", base[:-2]
    else:
        raise ValueError("enter an infinitive ending in -ar, -er, or -ir")
    if len(base) < 2:
        raise ValueError("enter an infinitive ending in -ar, -er, or -ir")

    if base in IRREGULAR and tense in IRREGULAR[base]:
        forms = list(IRREGULAR[base][tense])
    elif tense == "present" and base in STEM_CHANGE_PRESENT and STEM_CHANGE_PRESENT[base]:
        forms = list(STEM_CHANGE_PRESENT[base][2])
    elif tense == "present":
        forms = _regular_present(stem, ending)
    elif tense == "preterite":
        forms = _regular_preterite(stem, ending)
    elif tense == "imperfect":
        forms = _regular_imperfect(stem, ending)
    else:
        forms = _regular_future(base)

    if reflexive:
        reflexive_pronouns = ("me", "te", "se", "nos", "se", "se")
        forms = [f"{p} {f}" for p, f in zip(reflexive_pronouns, forms)]

    rows = [{"pronoun": p, "form": f} for p, f in zip(PRONOUNS, forms)]
    return {
        "verb": raw,
        "infinitive": base + ("se" if reflexive else ""),
        "tense": tense,
        "pronouns_note": "Mexican Spanish — ustedes (no vosotros)",
        "forms": rows,
    }
