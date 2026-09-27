"""
Batchgenerator för bilder – v6.

Förändringar mot v5:
- Modellen läses från Inställningar-bladet (nyckel: 'modell').
  Om nyckeln saknas används Flux Pro 1.1 som förut.
- Output sparas i en undermapp per modell, så samma kort kan genereras
  genom flera modeller sida vid sida utan att skriva över varandra.
- API-nyckeln läses i första hand från miljövariabeln FAL_KEY och
  faller tillbaka på Excel-värdet. Lägg nyckeln i miljön för säkerhet.

Kör:
    python generate_images_v6.py
"""
import os, time, urllib.request
from pathlib import Path

import fal_client
from PIL import Image
from shape_mask import apply_mask

try:
    import openpyxl
    import numpy as np
except ImportError:
    print("Saknade paket – kör: python -m pip install openpyxl numpy pillow fal-client")
    raise SystemExit(1)


HERE = Path(__file__).resolve().parent


# ─────────────────────────────────────────────────────────────────────────────
# FÄRGSYSTEM — läses från färgschema.xlsx, mappas till kategori
# ─────────────────────────────────────────────────────────────────────────────

# Kategori → färgnamn (samma mappning som i big_bang_skriv_om_prompter.py)
KATEGORI_FÄRG = {
    "BRF":                "Åke Sundvall Rödgrå",
    "Hyresrätt":          "Åke Sundvall Röd",
    "KONTOR":             "Åke Sundvall Grå",
    "LOKAL":              "Åke Sundvall Mörkgrå",
    "FÖRSKOLOR":          "Skiffer",
    "Politikkort":        "Åke Sundvall Träbrun",
    "Dialogkort":         "Åke Sundvall Träbrun",
    "Leverantörer":       "Havsblå",
    "Organisation":       "Havsblå",
    "Händelsekort":       "Havsblå",
    "Projektchef":        "Åke Sundvall Träbrun",
    "Arbetschef":         "Åke Sundvall Träbrun",
    "Projekt":            "Åke Sundvall Träbrun",
    "Faskort":            "Åke Sundvall Skogsgrön",
    "Garantibesiktning":  "Åke Sundvall Skogsgrön",
    "Konsekvenskort":     "Åke Sundvall Skogsgrön",
    "Företagskultur":     "Åke Sundvall Skogsgrön",
    "GENOMFÖRANDEFAS":    "Åke Sundvall Skogsgrön",
    "Fastighetschef":     "Åke Sundvall Röd",
    "Fastighetstekniker": "Åke Sundvall Röd",
    "Personal":           "Åke Sundvall Röd",
    "Due Diligence":      "Åke Sundvall Röd",
    "Förvaltning":        "Åke Sundvall Röd",
    "Moderbolagslån":     "Åke Sundvall Röd",
    "Omvärldskort":       "Åke Sundvall Röd",
    "Yield":              "Åke Sundvall Röd",
    "Instutition":        "Åke Sundvall Grå",
}


def hex_till_rgb(h: str) -> dict:
    """#F2EFE9 → {'r': 242, 'g': 239, 'b': 233}"""
    h = h.lstrip("#")
    return {"r": int(h[0:2], 16), "g": int(h[2:4], 16), "b": int(h[4:6], 16)}


def läs_färgschema(path: Path) -> dict:
    """{färgnamn: {'hex', 'hex_mörk', 'rgb', 'rgb_mörk'}}"""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Färger"]
    färger = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] and row[2]:
            hex_ljus = str(row[2]).strip()
            hex_mörk = str(row[4]).strip() if row[4] else hex_ljus
            färger[str(row[1]).strip()] = {
                "hex":      hex_ljus,
                "hex_mörk": hex_mörk,
                "rgb":      hex_till_rgb(hex_ljus),
                "rgb_mörk": hex_till_rgb(hex_mörk),
            }
    return färger


def palett_för_kategori(kategori: str, färger: dict) -> list:
    """Bygg en 5-färgs palett för en kategori att skicka till Recraft."""
    färg_namn = KATEGORI_FÄRG.get(kategori, "Åke Sundvall Grå")
    huvud = färger.get(färg_namn)
    if not huvud:
        return []

    # Fasta bas-färger som finns i varje kort
    bakgrund = färger.get("Åke Sundvall Rödgrå")        # papperston
    neutral  = färger.get("Åke Sundvall Ljusgrå")       # mjuk neutral
    mork_text = färger.get("Åke Sundvall Mörkgrå")      # text/linework

    palett = []
    palett.append(huvud["rgb"])
    if huvud["hex"] != huvud["hex_mörk"]:
        palett.append(huvud["rgb_mörk"])
    if bakgrund:
        palett.append(bakgrund["rgb"])
    if neutral:
        palett.append(neutral["rgb"])
    if mork_text and len(palett) < 5:
        palett.append(mork_text["rgb"])

    return palett[:5]  # max 5



# ─────────────────────────────────────────────────────────────────────────────
# MODELLREGISTER
# Varje modell har egen endpoint och egen argument-byggare, så vi kan byta
# modell utan att röra prompterna.
# ─────────────────────────────────────────────────────────────────────────────

def _args_flux_pro_11(prompt, **_):
    return {
        "prompt":              prompt,
        "image_size":          "square_hd",
        "num_inference_steps": 28,
        "guidance_scale":      3.5,
        "num_images":          1,
        "safety_tolerance":    "5",
    }


def _args_flux_pro_11_ultra(prompt, **_):
    return {
        "prompt":           prompt,
        "aspect_ratio":     "1:1",
        "num_images":       1,
        "safety_tolerance": "5",
        "output_format":    "png",
    }


def _args_flux2_pro(prompt, **_):
    return {
        "prompt":              prompt,
        "image_size":          "square_hd",
        "num_images":          1,
        "safety_tolerance":    "5",
        "output_format":       "png",
    }


def _args_recraft_v3(prompt, colors=None, style=None, **_):
    """
    Recraft V3 stöder:
      - style: digital_illustration, digital_illustration/hand_drawn,
        digital_illustration/pastel_gradient, digital_illustration/grain m.fl.
      - colors: lista av dicts {"r": int, "g": int, "b": int} (upp till 5)
        som hårt låser paletten.
    """
    args = {
        "prompt":     prompt,
        "image_size": "square_hd",
        "style":      style or "digital_illustration/hand_drawn",
    }
    if colors:
        args["colors"] = colors
    return args


def _args_ideogram_v2(prompt, **_):
    return {
        "prompt":          prompt,
        "aspect_ratio":    "1:1",
        "style":           "design",
        "expand_prompt":   False,
    }


MODELS = {
    # nyckel i Inställningar   endpoint                           arg-byggare
    "flux-pro-1.1":       ("fal-ai/flux-pro/v1.1",        _args_flux_pro_11),
    "flux-pro-1.1-ultra": ("fal-ai/flux-pro/v1.1-ultra",  _args_flux_pro_11_ultra),
    "flux2-pro":          ("fal-ai/flux-pro",             _args_flux2_pro),
    "recraft-v3":         ("fal-ai/recraft-v3",           _args_recraft_v3),
    "ideogram-v2":        ("fal-ai/ideogram/v2",          _args_ideogram_v2),
}

DEFAULT_MODEL = "flux-pro-1.1"


# ─────────────────────────────────────────────────────────────────────────────
# STIL – gemensam grund för alla kort (oförändrad från v5)
# ─────────────────────────────────────────────────────────────────────────────

STYLE = (
    "vintage Scandinavian board game illustration, "
    "bold flat graphic shapes, clean ink outlines, "
    "rich saturated gouache colors, soft cel shading, "
    "centered single subject on plain warm light background, "
    "no environment, no ground, no horizon line, "
    "strong readable silhouette, charming and characterful"
)

NEGATIVE = (
    "absolutely no text, no letters, no words, no numbers, no logos, "
    "no buildings, no architecture, no facades, no windows, no rooftops, "
    "no watermark, no border, no frame, no photorealism, no 3d render, "
    "no manga, no anime, no superhero style, no dark horror"
)


# ─────────────────────────────────────────────────────────────────────────────
# NAMNBASERADE MOTIV (oförändrade från v5 – hela tabellen behålls)
# ─────────────────────────────────────────────────────────────────────────────

NAME_MOTIFS = {

    # ── BRF – natur och landskap ─────────────────────────────────────────────
    "eldningen":        "a single bold flame with ember glow, warm orange and deep red, rising upward",
    "gläntan":          "a sunlit forest clearing, dappled light breaking through tall birch trees above, seen from below",
    "horisonten":       "a clean horizon line where flat water meets an open sky, strong blue gradient",
    "klinten":          "a dramatic rocky cliff face, grey stone layered and bold, seen front-on",
    "kornet":           "a single tall ear of wheat grain, golden, on a plain background",
    "solrosen":         "a large sunflower in full bloom, bold yellow petals and dark center",
    "speglingen":       "a perfect reflection: two symmetrical trees mirrored in still water, minimal",
    "stigen":           "a winding forest path curving into soft distance, seen from above",
    "valvet":           "a single stone arch, warm sandstone, standing alone, strong and simple",
    "generell brf":     "a friendly round hill with a single tree, soft green, minimal",

    # ── Hyresrätt – natur och plats ──────────────────────────────────────────
    "bergsluttningen":  "a sloping hillside with layered rock and low scrub, seen in profile",
    "fågelsången":      "a small songbird perched on a single branch, beak open, musical",
    "hamnskiftet":      "a wooden dock post with a thick mooring rope, calm water beside it",
    "kvarnbacken":      "a traditional Swedish windmill on a gentle hill, bold silhouette",
    "lövängen":         "a cluster of birch leaves, fresh green, gently overlapping",
    "rosenlunden":      "a single open rose in bloom, soft pink, seen front-on",
    "sjöglimten":       "sunlight glinting on still lake water, abstract shimmer pattern",
    "stenbrynet":       "a clean-edged flat stone, grey-blue, like a whetstone, minimal",
    "åkanten":          "a river bank edge with reeds and calm water, seen in cross-section",
    "generell hyresrätt": "a simple leaf on still water, soft green, reflected",

    # ── FÖRSKOLOR – djur, natur och saga ─────────────────────────────────────
    "draklyan":         "a friendly cartoon dragon curled up in a cozy den, warm and inviting",
    "kullerbyttan":     "a cheerful round figure doing a somersault, playful and energetic",
    "nyckelpigan":      "a large bright ladybug from above, bold red with black spots",
    "regnbågen":        "a bold full rainbow arc against a soft sky, vibrant colors",
    "skattkistan":      "a small wooden treasure chest open with golden light spilling out",
    "smultronstället":  "a cluster of wild strawberries with leaves, red and green, close-up",
    "stjärnfröet":      "a single star-shaped seed pod catching the light, delicate and magical",
    "trollskogen":      "a dense magical forest with glowing mushrooms and crooked trees",
    "tussilagon":       "a single tussilago coltsfoot flower, bright yellow, early spring",
    "generell förskola": "a large friendly star shape, cheerful and bold",

    # ── LOKAL – schackpjäser ──────────────────────────────────────────────────
    "bonden":           "a single chess pawn piece, bold graphic form, top-lit",
    "drottningen":      "a single chess queen piece, elegant and tall, graphic",
    "gambiten":         "two chess pieces, one sacrificed fallen on its side, one standing",
    "kungen":           "a single chess king piece, heavy crown, solid and central",
    "löparen":          "a single chess bishop piece, tall diagonal form, graphic",
    "motdraget":        "two chess pieces facing each other on opposite squares, mirrored",
    "rokaden":          "a chess king and rook mid-castling maneuver, side by side",
    "springaren":       "a single chess knight piece, horse-head profile, bold graphic",
    "tornet":           "a single chess rook piece, tower form, thick and solid",
    "generell lokal":   "an abstract chess board corner with one piece, minimal",

    # ── KONTOR – rymd och navigation ─────────────────────────────────────────
    "bastionen":        "a solid stone fortress tower, bold and defensible, seen front-on",
    "fyrtornet":        "a lighthouse with a bright beacon beam, bold stripes, minimal",
    "galaxen":          "a swirling spiral galaxy, deep blue and violet with bright core",
    "kometbanan":       "a comet with a bright glowing head and long trailing tail",
    "kvadranten":       "an antique navigation quadrant instrument, brass, detailed",
    "nebulosan":        "a colorful cosmic nebula cloud, deep purple and teal, glowing",
    "observatoriet":    "a classic telescope pointing at the night sky, clean silhouette",
    "rymdaxeln":        "a vertical rocket launching, bold graphic plume, centered",
    "stjärnhamnen":     "a bright star above calm water, its reflection forming a harbor shape",
    "generell kontor":  "a single bright star, geometric and bold",

    # ── Händelsekort ─────────────────────────────────────────────────────────
    "riskbuffert":      "a bold shield with a coin stack behind it, protective symbol",
    "planering":        "a calendar page with a ruler and neat task marks",
    "förvaltning":      "a folder with a small key symbol on the cover",
    "driftnetto":       "a coin flowing in a smooth arc, simple and clean",
    "energiförbättring":"a lightning bolt growing from a leaf, energetic symbol",
    "hyresförhandling": "two hands reaching toward a document across a table",
    "sammanräkning":    "a clear tally board with stacked chips and a sum line",

    # ── Faskort ───────────────────────────────────────────────────────────────
    "genomförande":     "a bold forward arrow with progress marks, construction phase symbol",

    # ── Konsekvenskort ────────────────────────────────────────────────────────
    "konsekvens":       "a bold impact burst with a changed document emerging from it",

    # ── Institutioner ─────────────────────────────────────────────────────────
    "stadsbyggnadskontoret": "a drafting compass with an open city plan underneath",
    "skönhetsrådet":    "an ornate decorative seal or emblem, formal and symmetrical",
    "stadshuset":       "a civic crest shape, bold heraldic symbol, no building",
    "länsstyrelsen":    "a regional authority seal, formal circular emblem",

    # ── Due Diligence, Yield, Omvärld ─────────────────────────────────────────
    "due diligence":    "stacked documents with a magnifying glass highlighting one line",
    "bostäder":         "a calm rising line graph with a small house icon above it",
    "kommersiellt":     "a calm rising line graph with a small storefront icon above it",
    "omvärld":          "a simple globe with a single arrow and a calendar card",
    "moderbolagslån":   "a contract with one arrow and a coin stack, parent-loan symbol",

    # ── Garantibesiktning ─────────────────────────────────────────────────────
    "garantibesiktning": "a magnifying glass over a checklist with an approval stamp",

    # ── Fastighetschef ────────────────────────────────────────────────────────
    "fastighetschef bostäder":    "a confident property manager character with a folder and house icon",
    "fastighetschef kommersiellt":"a confident property manager with a tablet and storefront icon",
    "fastighetschef samhälle":    "a confident property manager with a civic document",
    "fastighetschef generalist":  "a confident property manager with a mixed clipboard",

    # ── Fastighetstekniker ────────────────────────────────────────────────────
    "fastighetstekniker bostäder":    "a building technician character with toolbelt and folder",
    "fastighetstekniker kommersiellt":"a building technician with tablet and storefront icon",
    "fastighetstekniker samhälle":    "a building technician with a civic repair document",
    "fastighetstekniker teknisk":     "a building technician with a single diagnostic tool",
    "fastighetstekniker generalist":  "a building technician with a mixed clipboard",

    # ── GENOMFÖRANDEFAS ───────────────────────────────────────────────────────
    "etablering":       "a construction site trailer with an orange safety flag",
    "mark":             "a compact yellow excavator, clean graphic silhouette",
    "husunderbyggnad":  "a concrete mixer drum with rebar and formwork block",
    "stomme":           "a structural steel frame module, beams and columns",
    "installationer":   "pipes, ducts and a control box neatly arranged",
    "fasader":          "a facade panel assembly with brackets, front view",
    "stomkomplettering":"partitions, a door and framing pieces arranged neatly",
    "invändiga ytskikt":"a paint roller, floor tile and trim sample arranged",

    # ── Projekt ───────────────────────────────────────────────────────────────
    "generell projekt":  "a rolled blueprint tied with a simple ribbon",
    "bya-klass":        "a floorplan sheet with a bold measurement arrow",
    "bta-klass":        "stacked floor diagrams with a gross area callout",

    # ── Förvaltning kvarter ───────────────────────────────────────────────────
    "förvaltning kvartal generell": "a folder with a small key on the cover, management symbol",
    "förvaltning kvartal 1":        "a bold number one inside a simple crest, first quarter",
    "förvaltning kvartal 2":        "a bold number two inside a simple crest, second quarter",
    "förvaltning kvartal 3":        "a bold number three inside a simple crest, third quarter",
    "förvaltning kvartal 4":        "a bold number four inside a simple crest, fourth quarter",
}


# ─────────────────────────────────────────────────────────────────────────────
# KATEGORIBASERADE STILAR
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_STYLE_EXTRA = {
    "BRF":           "nature and landscape motif, soft natural palette, serene mood",
    "Hyresrätt":     "nature and place motif, warm earthy palette, calm mood",
    "FÖRSKOLOR":     "playful children's illustration, bright cheerful palette, friendly and warm",
    "LOKAL":         "bold graphic chess piece, dramatic chiaroscuro, ivory and dark wood tones",
    "KONTOR":        "cosmic and navigation motif, deep space palette, dramatic lighting",
    "Händelsekort":  "clean symbol design, bold icon style, clear readable form",
    "Faskort":       "clear phase marker icon, bold graphic, construction palette",
    "Konsekvenskort":"dramatic impact symbol, bold contrast, clear message",
    "Leverantörer":  "clean technical illustration, construction materials palette, clear detail",
    "Organisation":  "group character illustration, professional palette, team composition",
    "Fastighetschef":"character illustration, professional attire, confident pose",
    "Fastighetstekniker": "character illustration, work attire, practical tools visible",
    "Personal":      "character illustration, professional context, clear readable pose",
    "Företagskultur":"group character illustration, warm collaborative mood",
    "Instutition":   "civic emblem style, formal palette, heraldic feeling",
    "Politikkort":   "formal document and civic symbol style",
    "Dialogkort":    "conversational character illustration, open body language",
    "Omvärldskort":  "world and environment symbol, globe motif, geographic palette",
    "Garantibesiktning": "inspection symbol style, checklist and tool motif",
    "Yield":         "clean financial chart style, calm colors, simple upward line",
    "Due Diligence": "document review symbol, magnifying glass motif",
    "Moderbolagslån":"financial symbol style, contract and coin motif",
    "GENOMFÖRANDEFAS":"construction object illustration, site equipment palette",
    "Projekt":       "blueprint and measurement symbol style",
    "Förvaltning":   "management symbol style, property management palette",
}


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTBYGGARE (oförändrad från v5)
# ─────────────────────────────────────────────────────────────────────────────

def lookup_motif(row):
    namn     = str(row.get("namn")     or "").strip().lower()
    kategori = str(row.get("kategori") or "").strip()

    prefix_candidates = [
        kategori.lower(),
        "brf", "hyresrätt", "förskolor", "lokal", "kontor",
        "fastighetschef", "fastighetstekniker", "förvaltning",
        "genomförandefas",
    ]
    short_namn = namn
    for prefix in prefix_candidates:
        if short_namn.startswith(prefix + " "):
            short_namn = short_namn[len(prefix):].strip()
            break

    for key in [short_namn, namn, f"{kategori.lower()} {short_namn}"]:
        if key in NAME_MOTIFS:
            return NAME_MOTIFS[key]

    namn_en = str(row.get("namn_en") or "").strip()
    if namn_en and "building" not in namn_en.lower() and "front view" not in namn_en.lower():
        return namn_en

    cat_generics = {
        "BRF":           "a calm natural landscape with a single symbolic element",
        "Hyresrätt":     "a gentle natural scene with one clear symbol",
        "FÖRSKOLOR":     "a friendly colorful symbol, playful and warm",
        "LOKAL":         "a chess piece, bold graphic form",
        "KONTOR":        "a cosmic symbol, space and navigation",
        "Leverantörer":  "a construction material or machine, clear and bold",
        "Organisation":  "a small group of professional characters",
        "Fastighetschef":"a professional character with a property management prop",
        "Fastighetstekniker": "a technical character with a building maintenance tool",
        "Personal":      "a professional character with a clear work prop",
    }
    return cat_generics.get(kategori, f"a bold graphic symbol representing {namn}")


_person_counter = 0

def build_prompt(row, _prompt_delar):
    global _person_counter

    prompt_v6 = str(row.get("prompt_v6") or "").strip()
    if prompt_v6:
        if "single person only" in prompt_v6 or "human icon" in prompt_v6:
            _person_counter += 1
            if _person_counter % 2 == 0:
                prompt_v6 = prompt_v6.replace(
                    "single person only",
                    "single person only, clearly female presenting"
                )
        return prompt_v6

    motif        = lookup_motif(row)
    kategori     = str(row.get("kategori") or "").strip()
    style_extra  = CATEGORY_STYLE_EXTRA.get(kategori, "")

    parts = [motif, STYLE, style_extra, NEGATIVE]
    return ", ".join(p for p in parts if p)


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL-LADDNING (oförändrad från v5, förutom att 'modell' plockas ut)
# ─────────────────────────────────────────────────────────────────────────────

def resolve_xlsx_path():
    preferred = [
        HERE / "bilder_v5_finjusterad_merged_v6.xlsx",
        HERE / "bilder.xlsx",
    ]
    for p in preferred:
        if p.exists():
            return p
    candidates = sorted(
        p for p in HERE.glob("*.xlsx")
        if not p.name.startswith("~$")
    )
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        f"Hittade ingen Excel-fil i {HERE}. Lägg workbooken i samma mapp som skriptet."
    )


XLSX_PATH = resolve_xlsx_path()


def load_excel(path):
    import shutil, tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        shutil.copy2(path, tmp.name)
        wb = openpyxl.load_workbook(tmp.name, data_only=True)
    except Exception as e:
        raise RuntimeError(
            f"Kan inte öppna {path}\n  → Stäng filen i Excel.\n  Fel: {e}"
        )
    finally:
        os.unlink(tmp.name)

    settings = {}
    for row in wb["Inställningar"].iter_rows(min_row=2, values_only=True):
        if row[0]:
            settings[str(row[0]).strip()] = str(row[1]).strip() if row[1] is not None else ""

    prompt_delar = {}

    COL_MAP = {
        "Unikt ID":                  "id",
        "Kategori":                  "kategori",
        "Namn (visas i spelet)":     "namn",
        "Engelsk tolkning (prompt)": "namn_en",
        "Extra nyckelord":           "nyckelord",
        "Bakgrundsfärg (hex)":       "fill_color",
        "Ikonfärg (hex)":            "line_color",
        "Bildform":                  "bildform",
        "Utfilnamn (utan .png)":     "utfil",
        "Status":                    "status",
        "Typ v6":                    "typ_v6",
        "Formtyp v6":                "formtyp_v6",
        "Prompt v6":                 "prompt_v6",
    }
    ws = wb["Bilder"]
    raw_headers = [c.value for c in ws[1]]
    headers = [
        COL_MAP.get(str(h).strip(), str(h).strip()) if h else ""
        for h in raw_headers
    ]

    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if any(row):
            d = dict(zip(headers, row))
            if d.get("id") and (d.get("prompt_v6") or d.get("namn_en") or d.get("namn")):
                rows.append(d)

    return settings, prompt_delar, rows


# ─────────────────────────────────────────────────────────────────────────────
# BILDGENERERING
# ─────────────────────────────────────────────────────────────────────────────

def generate_image(prompt, output_path, bildform, api_key, model_key,
                   max_attempts=3, **extra_args):
    """
    model_key är en nyckel i MODELS. Faller tillbaka på DEFAULT_MODEL om okänd.
    extra_args (t.ex. colors=, style=) skickas vidare till arg-byggaren för
    modeller som stöder dem (Recraft V3).
    """
    os.environ["FAL_KEY"] = api_key
    prompt_ascii = prompt.encode("ascii", errors="replace").decode("ascii").replace("?", "")

    if model_key not in MODELS:
        print(f"           Okänd modell '{model_key}' – faller tillbaka på {DEFAULT_MODEL}")
        model_key = DEFAULT_MODEL
    endpoint, build_args = MODELS[model_key]

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            print(f"           Försök {attempt}/{max_attempts}...")
        result = fal_client.run(
            endpoint,
            arguments=build_args(prompt_ascii, **extra_args),
        )

        tmp = output_path + ".tmp.png"
        urllib.request.urlretrieve(result["images"][0]["url"], tmp)
        img = Image.open(tmp).convert("RGBA")

        arr = np.array(img.convert("L"))
        if arr.std() < 10:
            os.remove(tmp)
            print("           Tomt motiv – försöker igen...")
            time.sleep(2)
            continue

        img = apply_mask(img, bildform or "rund")
        img.save(output_path, "PNG")
        os.remove(tmp)
        return

    raise RuntimeError(f"Tomt motiv efter {max_attempts} försök")


# ─────────────────────────────────────────────────────────────────────────────
# HUVUDPROGRAM
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"Excel: {XLSX_PATH.name}")
    settings, prompt_delar, rows = load_excel(XLSX_PATH)

    # API-nyckel: miljövariabel före Excel
    api_key = os.environ.get("FAL_KEY") or settings.get("API-nyckel", "")
    if not api_key:
        print("Saknar API-nyckel.")
        print("  Sätt miljövariabel FAL_KEY eller lägg till 'API-nyckel' i Inställningar-bladet.")
        return

    # Modellväljare
    model_key = settings.get("modell") or DEFAULT_MODEL
    if model_key not in MODELS:
        print(f"⚠ Okänd modell '{model_key}'. Giltiga värden: {', '.join(MODELS.keys())}")
        print(f"  Använder {DEFAULT_MODEL}.")
        model_key = DEFAULT_MODEL
    print(f"Modell: {model_key}")

    # Recraft-stil (läses från Inställningar, default hand_drawn)
    recraft_style = settings.get("recraft_stil") or "digital_illustration/hand_drawn"
    if model_key == "recraft-v3":
        print(f"Recraft-stil: {recraft_style}")

    # Ladda färgschema om det finns (krävs bara för Recraft med färglåsning)
    färger = {}
    färg_path = HERE / "färgschema.xlsx"
    if färg_path.exists():
        try:
            färger = läs_färgschema(färg_path)
            print(f"Färgschema: {len(färger)} färger laddade från {färg_path.name}")
        except Exception as e:
            print(f"⚠ Kunde inte läsa färgschema: {e}")
    else:
        print(f"ℹ Inget färgschema hittades på {färg_path} — kör utan färglåsning")

    output_mapp = settings.get("output_mapp", "")
    max_forsok  = int(settings.get("max_försök", 3))
    fordrojning = float(settings.get("fördröjning_sek", 2))
    test_mode   = settings.get("test_läge", "FALSE").upper() == "TRUE"
    test_id     = settings.get("test_id", "").strip()

    running_local = os.name == "nt"
    base_out = output_mapp if (running_local and output_mapp) else str(HERE / "output_images")
    out_dir = os.path.join(base_out, model_key)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Sparar i: {out_dir}")

    if test_mode:
        rows = [r for r in rows if str(r.get("id") or "").strip() == test_id]
        if not rows:
            print(f"TESTLÄGE: Hittade inte id='{test_id}'")
            return
        print(f"TESTLÄGE – genererar bara: {rows[0].get('namn')}\n")
    else:
        print(f"Genererar bilder för {len(rows)} poster...\n")

    stats = {"genererad": 0, "fanns": 0, "fel": 0}

    for i, row in enumerate(rows):
        namn     = str(row.get("namn") or "").strip()
        utfil    = str(row.get("utfil") or row.get("id") or namn).strip()
        for ch in r'\/:*?"<>|':
            utfil = utfil.replace(ch, "_")
        bildform = str(row.get("bildform") or "rund").strip()
        out_path = os.path.join(out_dir, f"{utfil}.png")

        if not test_mode and os.path.exists(out_path):
            print(f"  [{i+1:3}/{len(rows)}] {namn}  – finns redan, hoppar över")
            stats["fanns"] += 1
            continue

        prompt = build_prompt(row, prompt_delar)
        kategori = str(row.get("kategori") or "").strip()

        # Bygg extra args till arg-byggaren
        extra = {}
        if model_key == "recraft-v3":
            extra["style"] = recraft_style
            if färger:
                palett = palett_för_kategori(kategori, färger)
                if palett:
                    extra["colors"] = palett

        print(f"  [{i+1:3}/{len(rows)}] {namn}  ({bildform})  [{kategori}]")
        if model_key == "recraft-v3" and "colors" in extra:
            hex_preview = [f"#{c['r']:02x}{c['g']:02x}{c['b']:02x}" for c in extra["colors"][:3]]
            print(f"           palett: {', '.join(hex_preview)}...")
        print(f"           {prompt[:140]}...")

        try:
            generate_image(prompt, out_path, bildform, api_key, model_key,
                           max_attempts=max_forsok, **extra)
            print(f"           Sparad: {out_path}")
            stats["genererad"] += 1
        except Exception as e:
            print(f"           Fel: {e}")
            stats["fel"] += 1

        if i < len(rows) - 1:
            time.sleep(fordrojning)

    print(f"\nKlart!  Genererade: {stats['genererad']}  Fanns redan: {stats['fanns']}  Fel: {stats['fel']}")


if __name__ == "__main__":
    main()

