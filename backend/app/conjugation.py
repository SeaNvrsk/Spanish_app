"""Spanish verb conjugation (Mexican usage — no vosotros). Rule-based, not AI."""

import unicodedata

PRONOUNS = ("yo", "tú", "él/ella/usted", "nosotros", "ustedes", "ellos/ellas")

TENSES = ("present", "preterite", "imperfect", "future")

# --- Full irregular paradigms (all tenses) ---------------------------------
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

# --- Present: full paradigm overrides --------------------------------------
PRESENT_OVERRIDE = {
    "pensar": ["pienso", "piensas", "piensa", "pensamos", "piensan", "piensan"],
    "entender": ["entiendo", "entiendes", "entiende", "entendemos", "entienden", "entienden"],
    "preferir": ["prefiero", "prefieres", "prefiere", "preferimos", "prefieren", "prefieren"],
    "empezar": ["empiezo", "empiezas", "empieza", "empezamos", "empiezan", "empiezan"],
    "comenzar": ["comienzo", "comienzas", "comienza", "comenzamos", "comienzan", "comienzan"],
    "cerrar": ["cierro", "cierras", "cierra", "cerramos", "cierran", "cierran"],
    "dormir": ["duermo", "duermes", "duerme", "dormimos", "duermen", "duermen"],
    "volver": ["vuelvo", "vuelves", "vuelve", "volvemos", "vuelven", "vuelven"],
    "pedir": ["pido", "pides", "pide", "pedimos", "piden", "piden"],
    "servir": ["sirvo", "sirves", "sirve", "servimos", "sirven", "sirven"],
    "seguir": ["sigo", "sigues", "sigue", "seguimos", "siguen", "siguen"],
    "repetir": ["repito", "repites", "repite", "repetimos", "repiten", "repiten"],
    "sentir": ["siento", "sientes", "siente", "sentimos", "sienten", "sienten"],
    "caer": ["caigo", "caes", "cae", "caemos", "caen", "caen"],
    "traer": ["traigo", "traes", "trae", "traemos", "traen", "traen"],
    "oir": ["oigo", "oyes", "oye", "oímos", "oyen", "oyen"],
    "oír": ["oigo", "oyes", "oye", "oímos", "oyen", "oyen"],
    "valer": ["valgo", "vales", "vale", "valemos", "valen", "valen"],
    "jugar": ["juego", "juegas", "juega", "jugamos", "juegan", "juegan"],
    "conocer": ["conozco", "conoces", "conoce", "conocemos", "conocen", "conocen"],
    "traducir": ["traduzco", "traduces", "traduce", "traducimos", "traducen", "traducen"],
    "producir": ["produzco", "produces", "produce", "producimos", "producen", "producen"],
}

# --- Preterite: full paradigm overrides ------------------------------------
PRETERITE_OVERRIDE = {
    "leer": ["leí", "leíste", "leyó", "leímos", "leyeron", "leyeron"],
    "creer": ["creí", "creíste", "creyó", "creímos", "creyeron", "creyeron"],
    "oir": ["oí", "oíste", "oyó", "oímos", "oyeron", "oyeron"],
    "oír": ["oí", "oíste", "oyó", "oímos", "oyeron", "oyeron"],
    "caer": ["caí", "caíste", "cayó", "caímos", "cayeron", "cayeron"],
    "traer": ["traje", "trajiste", "trajo", "trajimos", "trajeron", "trajeron"],
    "conducir": ["conduje", "conduciste", "condujo", "conducimos", "condujeron", "condujeron"],
    "traducir": ["traduje", "tradujiste", "tradujo", "tradujimos", "tradujeron", "tradujeron"],
    "producir": ["produje", "produjiste", "produjo", "produjimos", "produjeron", "produjeron"],
    "reducir": ["reduje", "redujiste", "redujo", "redujimos", "redujeron", "redujeron"],
    "introducir": ["introduje", "introdujiste", "introdujo", "introdujimos", "introdujeron", "introdujeron"],
    "andar": ["anduve", "anduviste", "anduvo", "anduvimos", "anduvieron", "anduvieron"],
}

# -IR preterite: e→i / o→u in 3rd person (él, ellos)
PRETERITE_IR_E_TO_I = frozenset({
    "pedir", "servir", "repetir", "seguir", "sentir", "mentir", "vestir",
    "preferir", "medir", "rendir",
})
PRETERITE_IR_O_TO_U = frozenset({"dormir", "morir"})

# Future: irregular stem (drop infinitive vowel, add endings)
FUTURE_STEM = {
    "salir": "saldr",
    "tener": "tendr",
    "venir": "vendr",
    "decir": "dir",
    "hacer": "har",
    "poder": "podr",
    "querer": "querr",
    "saber": "sabr",
    "poner": "pondr",
    "caber": "cabr",
    "valer": "valdr",
    "haber": "habr",
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower().strip())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _strip_reflexive(verb: str) -> tuple[str, bool]:
    if verb.endswith("se") and len(verb) > 3:
        return verb[:-2], True
    return verb, False


def _replace_last_vowel_in_stem(stem: str, from_v: str, to_v: str) -> str:
    for i in range(len(stem) - 1, -1, -1):
        if stem[i] == from_v:
            return stem[:i] + to_v + stem[i + 1 :]
    return stem


def _regular_present(stem: str, ending: str) -> list[str]:
    if ending == "ar":
        return [stem + s for s in ("o", "as", "a", "amos", "an", "an")]
    if ending in ("er", "ir"):
        nos = "emos" if ending == "er" else "imos"
        return [stem + s for s in ("o", "es", "e", nos, "en", "en")]
    raise ValueError("invalid ending")


def _preterite_ar_yo(stem: str) -> str:
    """Spelling changes before -é in yo preterite (-car, -gar, -zar)."""
    if stem.endswith("c"):
        return stem[:-1] + "qué"
    if stem.endswith("g"):
        return stem[:-1] + "gué"
    if stem.endswith("z"):
        return stem[:-1] + "cé"
    return stem + "é"


def _preterite_ar(stem: str) -> list[str]:
    yo = _preterite_ar_yo(stem)
    return [yo, stem + "aste", stem + "ó", stem + "amos", stem + "aron", stem + "aron"]


def _preterite_er_ir(stem: str, infinitive: str) -> list[str]:
    """-ER/-IR preterite; vowel stems use y in 3rd person; stem change in -ir."""
    if stem and stem[-1] in "aeiou":
        return [stem + s for s in ("í", "íste", "yó", "ímos", "yeron", "yeron")]

    forms = [stem + s for s in ("í", "iste", "ió", "imos", "ieron", "ieron")]
    if infinitive in PRETERITE_IR_E_TO_I:
        s3 = _replace_last_vowel_in_stem(stem, "e", "i")
        forms[2] = s3 + "ió"
        forms[4] = forms[5] = s3 + "ieron"
    elif infinitive in PRETERITE_IR_O_TO_U:
        s3 = _replace_last_vowel_in_stem(stem, "o", "u")
        forms[2] = s3 + "ió"
        forms[4] = forms[5] = s3 + "ieron"
    return forms


def _regular_imperfect(stem: str, ending: str) -> list[str]:
    if ending == "ar":
        return [stem + s for s in ("aba", "abas", "aba", "ábamos", "aban", "aban")]
    return [stem + s for s in ("ía", "ías", "ía", "íamos", "ían", "ían")]


def _future_from_stem(stem: str) -> list[str]:
    return [stem + s for s in ("é", "ás", "á", "emos", "án", "án")]


def _regular_future(infinitive: str) -> list[str]:
    return _future_from_stem(infinitive)


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
    elif tense == "present" and base in PRESENT_OVERRIDE:
        forms = list(PRESENT_OVERRIDE[base])
    elif tense == "present":
        forms = _regular_present(stem, ending)
    elif tense == "preterite" and base in PRETERITE_OVERRIDE:
        forms = list(PRETERITE_OVERRIDE[base])
    elif tense == "preterite" and ending == "ar":
        forms = _preterite_ar(stem)
    elif tense == "preterite":
        forms = _preterite_er_ir(stem, base)
    elif tense == "imperfect":
        forms = _regular_imperfect(stem, ending)
    elif base in FUTURE_STEM:
        forms = _future_from_stem(FUTURE_STEM[base])
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
