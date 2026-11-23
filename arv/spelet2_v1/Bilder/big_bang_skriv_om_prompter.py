"""
big_bang_skriv_om_prompter.py
─────────────────────────────────────────────────────────────────────────────

Skriver om ALLA Prompt v6-fält i bilder.xlsx enligt picture-book-stilen,
med motiv hämtade från NAME_MOTIFS och färger från färgschema.xlsx.

Regler:
- Inga byggnader som motiv — utom för kategorin 'Instutition' där byggnad
  ÄR själva identiteten (Stadshuset, Länsstyrelsen osv). Där beskrivs
  byggnaden som picture-book, inte piktogram.
- Personkort (Typ v6 = 'human' eller 'group') använder karaktärsprompt
  med Rekvisita v6 som prop.
- Objektkort (Typ v6 = 'object') använder motivet från NAME_MOTIFS.
- Alla prompter säger uttryckligen vad stilen är och vad den INTE är.

Kör:
    python big_bang_skriv_om_prompter.py sökväg/till/bilder.xlsx sökväg/till/färgschema.xlsx

Om sökvägar inte anges letas båda filerna i skriptets mapp.

Backup av Prompt v6 sparas i kolumnen 'Prompt v6 (original backup)'.
En kopia av hela Excel-filen sparas som <filnamn>_FÖRE_bigbang.xlsx.
"""

import sys
import shutil
from pathlib import Path

import openpyxl


# ─────────────────────────────────────────────────────────────────────────────
# MOTIVKATALOG — vad varje kort ska föreställa
# (kopplad på Unikt ID, case-insensitive match)
# ─────────────────────────────────────────────────────────────────────────────

MOTIV = {
    # ── BRF — natur, landskap, element ───────────────────────────────────────
    "brf_eldningen":    "a single warm flame with glowing embers, curling upward",
    "brf_gläntan":      "a sunlit forest clearing seen from within, dappled light falling between tall birches",
    "brf_horisonten":   "a wide calm horizon line where water meets sky, a single sailboat in the distance",
    "brf_klinten":      "a dramatic rocky cliff face with layered stone and a single pine clinging to its top",
    "brf_kornet":       "a single tall ear of wheat, heavy with golden grain, bending slightly",
    "brf_solrosen":     "a single large sunflower in full bloom, head tilted toward the light, strong stem and leaves",
    "brf_speglingen":   "two trees mirrored in still water, perfectly symmetrical reflection",
    "brf_stigen":       "a winding forest path curving into the distance, soft undergrowth on each side",
    "brf_valvet":       "a single weathered stone arch standing alone in a meadow",
    "brf_generell":     "a friendly rounded hill with a single tree on its crest",

    # ── Hyresrätt — natur och plats ──────────────────────────────────────────
    "hyresrätt_bergsluttningen": "a sloping hillside with layered rock, low bushes and a single juniper",
    "hyresrätt_fågelsången":     "a small songbird perched on a curling branch, beak open in song",
    "hyresrätt_hamnskiftet":     "a wooden dock post with a thick mooring rope coiled around it, calm water beside",
    "hyresrätt_kvarnbacken":     "a traditional Swedish windmill on a gentle hill, sails turning slowly",
    "hyresrätt_lövängen":        "a cluster of fresh birch leaves, layered and overlapping, catching the light",
    "hyresrätt_rosenlunden":     "a single open rose in full bloom, soft petals and a strong leafy stem",
    "hyresrätt_sjöglimten":      "sunlight glinting on still lake water, a shimmering ripple pattern",
    "hyresrätt_stenbrynet":      "a smooth flat whetstone resting at the edge of a grassy path",
    "hyresrätt_åkanten":         "a river bank with tall reeds and calm flowing water",
    "hyresrätt_generell":        "a single leaf floating on still water, its reflection just visible",

    # ── FÖRSKOLOR — djur, natur och saga ────────────────────────────────────
    "förskolor_draklyan":        "a friendly little dragon curled up in a cozy den, smoke puffing gently",
    "förskolor_kullerbyttan":    "a cheerful child mid-somersault, limbs tumbling, joyful",
    "förskolor_nyckelpigan":     "a plump ladybug seen from above, resting on a curling green leaf, wing-case slightly open",
    "förskolor_regnbågen":       "a bold arching rainbow above a small cloud, vibrant bands of color",
    "förskolor_skattkistan":     "a small wooden treasure chest open, warm golden light spilling out",
    "förskolor_smultronstället": "a cluster of wild strawberries with leaves, ripe red fruit, close up",
    "förskolor_stjärnfröet":     "a single star-shaped seed pod catching the light, delicate and magical",
    "förskolor_trollskogen":     "a dense enchanted forest with glowing mushrooms and crooked trees",
    "förskolor_tussilagon":      "a single tussilago coltsfoot flower, bright yellow, pushing up through spring soil",
    "förskolor_generell":        "a cheerful five-pointed star with a soft glow",

    # ── LOKAL — schackpjäser ─────────────────────────────────────────────────
    "lokal_bonden":      "a single chess pawn piece, turned wood, standing alone on a chequered square",
    "lokal_drottningen": "a single chess queen piece, elegant and tall, turned from warm wood",
    "lokal_gambiten":    "two chess pieces — one standing upright, one fallen on its side in sacrifice",
    "lokal_kungen":      "a single chess king piece, heavy crown, turned from dark wood",
    "lokal_löparen":     "a single chess bishop piece, tall diagonal form, turned wood",
    "lokal_motdraget":   "two chess pieces facing each other on opposite squares, a confrontation",
    "lokal_rokaden":     "a chess king and rook mid-castle, side by side, the iconic maneuver",
    "lokal_springaren":  "a single chess knight piece, horse-head profile, turned wood",
    "lokal_tornet":      "a single chess rook piece, tower form, solid and weighty",
    "lokal_generell":    "an abstract chessboard corner with one pawn centered",

    # ── KONTOR — rymd och navigation ─────────────────────────────────────────
    "kontor_bastionen":     "a solid stone fortress tower, weathered and defensible, standing alone",
    "kontor_fyrtornet":     "a classic red-and-white striped lighthouse on a rocky outcrop, warm lamp glowing, soft beam sweeping",
    "kontor_galaxen":       "a swirling spiral galaxy with a bright core, cosmic dust arms",
    "kontor_kometbanan":    "a comet with a bright glowing head and a long trailing tail across a dark sky",
    "kontor_kvadranten":    "an antique brass navigation quadrant, detailed instrument",
    "kontor_nebulosan":     "a colorful cosmic nebula cloud glowing against deep space",
    "kontor_observatoriet": "a classic telescope pointing up at the night sky, stars visible",
    "kontor_rymdaxeln":     "a vertical rocket at the moment of launch, bold plume beneath",
    "kontor_stjärnhamnen":  "a bright star above calm water, its reflection shaped like a harbor",
    "kontor_generell":      "a single bright five-pointed star against a dark sky",

    # ── Händelsekort ─────────────────────────────────────────────────────────
    "riskbuffert":        "a sturdy shield with a stack of coins behind it, a protective arrangement",
    "planering":          "a calendar page with a wooden ruler laid across it and neat task marks",
    "förvaltning_hk":     "a leather folder with a small brass key resting on its cover",
    "driftnetto":         "a single gold coin tracing a graceful arc through the air",
    "energiförbättring":  "a lightning bolt growing out of a fresh green leaf",
    "hyresförhandling":   "two hands meeting across a wooden table over an open document, one offering a pen",
    "sammanräkning":      "a tally board with stacked chips and a clear sum line",

    # ── Faskort ──────────────────────────────────────────────────────────────
    "genomförande_fas":   "a bold forward arrow with progress tick-marks beneath it",

    # ── Konsekvenskort ───────────────────────────────────────────────────────
    "konsekvens":         "a bold impact burst with a changed document emerging from its center",

    # ── Institutioner (byggnader ÄR motivet — picture-book, inte piktogram) ─
    "stadsbyggnadskontoret": "a stately Swedish civic planning office building with classical proportions, tall windows and a dignified entrance, seen from a slight angle, picture-book style",
    "skönhetsrådet":         "an ornate committee hall building with a decorative facade, tall windows and a formal entrance, picture-book style",
    "stadshuset":            "a grand Swedish city hall with a prominent tower and clock, brick facade, flags flying, picture-book style",
    "länsstyrelsen":         "a formal regional authority building with classical pillars, a dignified entrance and a coat of arms, picture-book style",

    # ── Due Diligence, Yield, Omvärld, Moderbolagslån ────────────────────────
    "due_diligence":      "a stack of documents with a magnifying glass hovering above, highlighting a single line",
    "yield_bostäder":     "a calm upward-rising line graph with a small house icon floating above",
    "yield_kommersiellt": "a calm upward-rising line graph with a small storefront icon floating above",
    "omvärld":            "a simple globe with a single directional arrow and a calendar card beside it",
    "moderbolagslån":     "a scroll-like contract with a directional arrow and a stack of coins, parent-loan symbol",

    # ── Garantibesiktning ────────────────────────────────────────────────────
    "garantibesiktning":  "a magnifying glass over a clipboard checklist with an approval stamp below",

    # ── Fastighetschef ───────────────────────────────────────────────────────
    "fastighetschef_bostader":     "a property manager standing in three-quarter view, holding a worn leather folder with a small house symbol on its cover",
    "fastighetschef_kommersiellt": "a property manager standing, holding a tablet showing a storefront symbol",
    "fastighetschef_samhalle":     "a property manager standing, holding a civic document folder with a small public building symbol",
    "fastighetschef_generalist":   "a property manager standing, holding a mixed clipboard with several small symbols",
    "fastighetschef_kommersiellt_2":"a property manager standing, holding a tablet and gesturing, storefront symbol visible",

    # ── Fastighetstekniker ──────────────────────────────────────────────────
    "fastighetstekniker_bostader":     "a building technician in work clothes holding a folder with a small house symbol, tool belt at waist",
    "fastighetstekniker_kommersiellt": "a building technician holding a tablet showing a storefront symbol, tool belt at waist",
    "fastighetstekniker_samhalle":     "a building technician holding a clipboard with a public building symbol, tool belt at waist",
    "fastighetstekniker_teknisk":      "a building technician holding a single diagnostic instrument, tool belt at waist",
    "fastighetstekniker_generalist":   "a building technician holding a mixed clipboard with several small symbols, tool belt at waist",

    # ── GENOMFÖRANDEFAS — site equipment & materials ─────────────────────────
    "etablering":         "a construction site trailer with an orange safety flag beside it",
    "mark":               "a compact yellow excavator, bucket lowered, ready to work",
    "husunderbyggnad":    "a concrete mixer drum with exposed rebar and a formwork block beside it",
    "stomme":             "a structural steel frame module with visible beams and columns",
    "installationer":     "pipes, ducts and a small control box arranged neatly together",
    "fasader":            "a facade panel with mounting brackets, front view",
    "stomkomplettering":  "a partition wall piece, a door leaf and framing components arranged together",
    "invändiga_ytskikt":  "a paint roller, a floor tile and a trim sample arranged together",

    # ── Projekt ──────────────────────────────────────────────────────────────
    "projekt_generell":   "a rolled architectural blueprint tied with a simple ribbon",
    "bya_klass":          "an architectural floorplan sheet with a bold measurement arrow",
    "bta_klass":          "stacked floor diagrams with a clear gross-area callout",

    # ── Förvaltning kvartal ──────────────────────────────────────────────────
    "förvaltning_kvartal_generell": "a leather management folder with a small brass key resting on its cover",
    "förvaltning_kvartal_q1":       "a stylized number one inside a simple heraldic crest",
    "förvaltning_kvartal_q2":       "a stylized number two inside a simple heraldic crest",
    "förvaltning_kvartal_q3":       "a stylized number three inside a simple heraldic crest",
    "förvaltning_kvartal_q4":       "a stylized number four inside a simple heraldic crest",

    # ── Projektchefer (karaktärer med individualitet) ───────────────────────
    "projektchef_pc1":  "a seasoned politician-like figure in a suit, holding a civic planning folder, shrewd and composed",
    "projektchef_pc2":  "a diplomatic figure with an open, welcoming posture, holding a negotiation folder",
    "projektchef_pc3":  "a canny city-hall veteran in a slightly rumpled suit, holding a stack of municipal documents",
    "projektchef_pc4":  "a visionary figure gazing forward, holding a rolled blueprint like a staff",
    "projektchef_pc5":  "an experienced older project manager with kind eyes, holding a worn leather folder",
    "projektchef_pc6":  "a sustainability-focused figure holding a green report folder, a small leaf on its cover",
    "projektchef_pc7":  "an energetic optimistic figure checking a clipboard with a schedule, pen in hand",
    "projektchef_pc8":  "a precise quality-focused figure with glasses, examining a detailed checklist",
    "projektchef_pc9":  "a networker mid-handshake or with an open map of contacts, warm and engaged",
    "projektchef_pc10": "an all-rounder figure with a multi-tabbed clipboard, balanced and capable",

    # ── Arbetschefer ─────────────────────────────────────────────────────────
    "arbetschef_ac1":  "a calm coordinator figure holding a whiteboard planning sheet with clear task lines",
    "arbetschef_ac2":  "a production specialist in work clothes, holding a detailed construction schedule",
    "arbetschef_ac3":  "a generalist figure with a mixed clipboard and a pencil behind the ear",
    "arbetschef_ac4":  "a communicator figure with an open posture, holding a communication board",
    "arbetschef_ac5":  "a safety-focused figure with a hard hat in one hand and a checklist in the other",
    "arbetschef_ac6":  "a scheduler figure holding a time-plan board, studying it intently",
    "arbetschef_ac7":  "a quality coach figure with a clipboard and a measuring tool",
    "arbetschef_ac8":  "a leadership figure with an encouraging posture, holding a leadership folder",
    "arbetschef_ac9":  "a sustainability engineer with a green site blueprint and a small plant sprig",
    "arbetschef_ac10": "a partnering expert figure with two clasped hands visible on a contract document",

    # ── Händelsekort — matcha faktiska ID:n ─────────────────────────────────
    "handelsekort_riskbuffert":       "a sturdy shield with a stack of coins behind it, a protective arrangement",
    "handelsekort_planering":         "a calendar page with a wooden ruler laid across it and neat task marks",
    "handelsekort_forvaltning":       "a leather folder with a small brass key resting on its cover",
    "driftnetto_forvaltning":         "a single gold coin tracing a graceful arc through the air",
    "energiförbättringar":            "a lightning bolt growing out of a fresh green leaf",

    # ── Övriga med ID-match ─────────────────────────────────────────────────
    "faskort_genomforande":                  "a bold forward arrow with progress tick-marks beneath it",
    "konsekvenskort_konsekvens":             "a bold impact burst with a changed document emerging from its center",
    "due_diligence_due_diligence":           "a stack of documents with a magnifying glass hovering above, highlighting a single line",
    "moderbolagslaan_moderbolagslaan":       "a scroll-like contract with a directional arrow and a stack of coins",
    "omvarldskort_omvarld":                  "a simple globe with a directional arrow and a calendar card beside it",
    "garantibesiktning_garantibesiktning":   "a magnifying glass over a clipboard checklist with an approval stamp below",
    "yield_bostader":                        "a calm upward-rising line graph with a small house icon floating above",
    "dialogkort_dialogkort":                 "two professionals facing each other in open conversation over a shared document",
    "politikkort_politikkort":               "a thoughtful civic figure standing with a rolled policy document under one arm",
    "personal_generell_personal":            "a professional staff member standing in three-quarter view with a clear work prop",

    # ── Institutioner (picture-book-byggnader) ──────────────────────────────
    "politikkort_stadsbyggnadskontoret": "a stately Swedish civic planning office building with classical proportions, tall windows and a dignified entrance, picture-book style",
    "politikkort_skonhetsradet":         "an ornate committee hall building with a decorative facade, tall windows and a formal entrance, picture-book style",
    "politikkort_stadshuset":            "a grand Swedish city hall with a prominent clock tower, brick facade and flags flying, picture-book style",
    "politikkort_lansstyrelsen":         "a formal regional authority building with classical pillars and a coat of arms above the entrance, picture-book style",

    # ── GENOMFÖRANDEFAS — matcha ID:n ───────────────────────────────────────
    "genomfors_etablering":       "a construction site trailer with an orange safety flag beside it",
    "genomfors_mark":             "a compact yellow excavator, bucket lowered, ready to work",
    "genomfors_husunderbyggnad":  "a concrete mixer drum with exposed rebar and a formwork block beside it",
    "genomfors_stomme":           "a structural steel frame module with visible beams and columns",
    "genomfors_installationer":   "pipes, ducts and a small control box arranged neatly together",
    "genomfors_fasader":          "a facade panel with mounting brackets, front view",
    "genomfors_stomkomplettering":"a partition wall piece, a door leaf and framing components arranged together",
    "genomfors_inv_ytskikt":      "a paint roller, a floor tile and a trim sample arranged together",

    # ── Projekt ──────────────────────────────────────────────────────────────
    "projekt":                    "a rolled architectural blueprint tied with a simple ribbon",
    "projekt_bya_klass":          "an architectural floorplan sheet with a bold measurement arrow across the building footprint",
    "projekt_bta_klass":          "stacked floor diagrams with a clear gross-area callout",

    # ── Fastighetstekniker varianter ────────────────────────────────────────
    "fastighetstekniker_bostader_2":     "a building technician in work clothes holding a folder with a house symbol, with a tool in the other hand, tool belt at waist",
    "fastighetstekniker_kommersiellt_2": "a building technician holding a tablet showing a storefront symbol, wearing work clothes",
    "fastighetstekniker_generalist_2":   "a building technician with a multi-tool belt and a mixed clipboard, capable and steady",

    # ── Förvaltning kvartal — matcha faktiska ID:n ──────────────────────────
    "förvaltning_kvartal_q1": "a stylized number one inside a simple heraldic crest",
    "förvaltning_kvartal_q2": "a stylized number two inside a simple heraldic crest",
    "förvaltning_kvartal_q3": "a stylized number three inside a simple heraldic crest",
    "förvaltning_kvartal_q4": "a stylized number four inside a simple heraldic crest",
}


# ─────────────────────────────────────────────────────────────────────────────
# LEVERANTÖRER — konstruktionsmaterial som picture-book-stilleben
# Koppla ID-substring till ett konkret motiv
# ─────────────────────────────────────────────────────────────────────────────

LEVERANTÖR_MOTIV = {
    "gravforetag":          "a small digger and a pile of excavated earth, tools resting against a mound",
    "markforetag":           "earthworks tools and a compacted earth surface with survey markers",
    "specialistforetag":      "specialist inspection tools arranged on a workbench, precise and clean",
    "markexpert":             "a surveyor's theodolite on a tripod with a marked stake beside it",
    "enkel_betonggrund":      "a simple concrete slab with visible rebar ends protruding",
    "standard_betongkonstruktion": "a concrete formwork panel with fresh poured concrete and rebar grid",
    "forstarkt_konstruktion": "a reinforced concrete beam with a dense rebar cage visible through cutaway",
    "betongexpert":           "a concrete sample cylinder next to a set of testing tools",
    "betong_lokalt":          "a small local concrete mixer with a shovel and a bag of cement",
    "betong_etablerat":       "a large industrial concrete mixer truck chute lowering into formwork",
    "prefab_element":         "a prefabricated concrete wall panel being lifted by crane hooks",
    "kl_tra":                 "cross-laminated timber panels stacked, showing the distinctive layered grain",
    "plattak_enkelt":         "a corrugated metal sheet with simple mounting clips",
    "plattak_standard":       "a standing-seam metal roof section showing the raised seams",
    "tegeltak":               "a pitched roof section with overlapping clay tiles in warm terracotta",
    "sedum_tak":              "a flat roof section covered in low sedum plants, green and textured",
    "puts":                   "a trowel spreading fresh render on a wall section, textured finish visible",
    "tegelfasad":             "a section of traditional Swedish brick facade with visible mortar lines",
    "natursten":              "a section of rough natural stone wall with varied block shapes and sizes",
    "pannatak":               "a pitched tile roof with traditional ceramic pantiles",
    "trafasad":               "a vertical wood cladding section with visible boards and a patina",
    "fonster":                "a traditional Swedish window with painted wooden frame and divided panes",
    "dorr":                   "a substantial wooden front door with iron hinges and a warm patina",
    "elinstallationer":       "an electrical distribution box with neat cable runs and labeled breakers",
    "ventilation":            "an HVAC duct junction with a small fan unit attached",
    "ror_sanitet":            "copper plumbing pipes forming a tidy manifold with valves",
    "varmesystem":            "a wall-mounted heating unit with pipes running down to a floor fitting",
    "innervaggar":            "a stud wall with insulation batts and one gypsum sheet partially installed",
    "undertak":               "a suspended ceiling grid with one acoustic tile partly slotted in",
    "golvbelaggning":         "floor samples fanned out — oak parquet, vinyl, linoleum, polished concrete",
    "malning":                "paint cans with brushes and a color swatch fan laid out on paper",
    "solceller":              "a rooftop solar panel array with visible cells and a small inverter box",
    "laddstolpar":            "an EV charging station with cable coiled neatly on its stand",
    "hissar":                 "an elevator door panel with a polished brass call button and indicator",
    "vvs_special":            "specialized plumbing fittings arranged like surgical tools on a cloth",
    "landskap_mark":          "landscaping elements — a young tree with root ball, a paving slab, grass sod",
    "landskap_bygg":          "a garden bench, paving stones and a small planted shrub arranged together",
    "lekutrustning":           "a wooden swing set and a small slide arranged together, playful",
    "standard_leverantor":    "a general builder's toolkit with hammer, measure and a folded plan",
    "etablerat_leverantor":   "a well-equipped professional toolbox open, premium tools inside",
    "sakerhetssystem":        "a small security camera and a keypad panel with a subtle warning light",
    "it_infra":               "a server rack with neat cable management and blinking status lights",
    "bygglednings":           "a site office desk with radios, plans and a hard hat",
    "miljobyggnad":           "a green building certificate plaque with small plant motifs",
    "svanen_cert":            "a swan-shaped eco-certification emblem on a clean document",
    "breeam_cert":            "a BREEAM-style rating plaque with a clear grade visible",
    "generell_leverantor":    "a general supplier's crate with mixed construction materials visible",
}


# ─────────────────────────────────────────────────────────────────────────────
# ORGANISATION & FÖRETAGSKULTUR — små gruppscener
# ─────────────────────────────────────────────────────────────────────────────

GRUPP_MOTIV = {
    "organisation_generell_organisation": "a balanced team of three professionals standing together around a shared plan",
    "organisation_operativt_team":     "an operations team of three in practical work clothes, gathered around a site plan",
    "organisation_operativt_team_1":   "a small rugged construction crew with hard hats, gathered around a blueprint",
    "organisation_operativt_team_2":   "a logistics team with a clipboard and a delivery schedule between them",
    "organisation_operativt_team_3":   "a command-center style team around a control desk with maps and radios",
    "organisation_operativt_team_4":   "a regional command team in formal-casual attire around a regional map",
    "organisation_stodfunktioner":     "a support-functions team of three in office attire, collaborating over documents",
    "organisation_stodfunktioner_1":   "a steady back-office trio working calmly around a desk with ledgers",
    "organisation_stodfunktioner_2":   "a service-center team at a counter helping each other with files",
    "organisation_stodfunktioner_3":   "a connector team with headsets and a shared contact map board",
    "organisation_stodfunktioner_4":   "an orderly administrative team with neat folders and stamps",
    "organisation_marknadsteam":       "a marketing team gathered around a presentation board, creative and animated",
    "organisation_marknadsteam_1":     "a small marketing group in a showroom corner with samples and brochures",
    "organisation_marknadsteam_2":     "a sales-pavilion team greeting visitors with site plans in hand",
    "organisation_marknadsteam_3":     "a modern studio team around a sleek presentation screen",
    "organisation_marknadsteam_4":     "a visualization team around a large model of a building, pointing and discussing",
    "organisation_digitalisering":     "a digital team around screens and a whiteboard with flowcharts",
    "organisation_digitalisering_1":   "an innovation-hub team in a bright space with sticky notes and tablets",
    "organisation_digitalisering_2":   "a data team around a large display of graphs and dashboards",
    "organisation_digitalisering_3":   "a smart-lab team with a prototype device between them",

    "foretagskultur_generell":       "a diverse small team standing together in relaxed posture, shared warmth",
    "foretagskultur_ledarskap":      "a leadership scene with one figure guiding two others over a shared plan",
    "foretagskultur_kommunikation":  "three figures in open conversation, gesturing and listening",
    "foretagskultur_samordning":     "three figures coordinating around a shared schedule, pointing to the same point",
    "foretagskultur_projektkunskap": "three figures sharing a project blueprint, one explaining, two learning",
    "foretagskultur_arbetsmiljo":    "three figures reviewing a safety checklist together, hard hats visible",
}


# ─────────────────────────────────────────────────────────────────────────────
# KATEGORI → FÄRGNAMN (enligt CSV-mappning i färgschema.xlsx)
# ─────────────────────────────────────────────────────────────────────────────

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
    "Instutition":        "Åke Sundvall Grå",   # bästa gissning
}


# ─────────────────────────────────────────────────────────────────────────────
# HJÄLPFUNKTIONER
# ─────────────────────────────────────────────────────────────────────────────

def läs_färgschema(path: Path) -> dict:
    """Returnerar {färgnamn: {'hex': '#...', 'hex_mörk': '#...', 'användning': '...'}}"""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Färger"]
    färger = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] and row[2]:
            färger[str(row[1]).strip()] = {
                "hex":      str(row[2]).strip(),
                "hex_mörk": (str(row[4]).strip() if row[4] else str(row[2]).strip()),
                "användning": str(row[5]).strip() if row[5] else "",
            }
    return färger


def hitta_fil(arg_index: int, default_namn: list) -> Path:
    if len(sys.argv) > arg_index:
        p = Path(sys.argv[arg_index]).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Hittar inte: {p}")
        return p
    here = Path(__file__).resolve().parent
    for namn in default_namn:
        kandidat = here / namn
        if kandidat.exists():
            return kandidat
    raise FileNotFoundError(
        f"Hittar inte någon av {default_namn} i {here}. "
        f"Ange sökväg som argument."
    )


def skapa_backup(path: Path) -> Path:
    backup = path.with_name(path.stem + "_FÖRE_bigbang" + path.suffix)
    shutil.copy2(path, backup)
    return backup


def säkerställ_backupkolumn(ws, källkolumn_rubrik="Prompt v6",
                            backupkolumn_rubrik="Prompt v6 (original backup)"):
    """Sätt in backupkolumn direkt efter Prompt v6 om den inte finns."""
    headers = [c.value for c in ws[1]]
    src_idx = headers.index(källkolumn_rubrik) + 1
    if backupkolumn_rubrik in headers:
        bak_idx = headers.index(backupkolumn_rubrik) + 1
        return src_idx, bak_idx
    bak_idx = src_idx + 1
    ws.insert_cols(bak_idx)
    ws.cell(row=1, column=bak_idx, value=backupkolumn_rubrik)
    return src_idx, bak_idx


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT-BYGGARE
# ─────────────────────────────────────────────────────────────────────────────

STIL_GEMENSAM = (
    "warm Scandinavian picture-book illustration, "
    "hand-painted gouache with visible brushstrokes and paper grain, "
    "varied ink linework, soft light from upper left, "
    "characterful and slightly imperfect"
)

NEGATIV_GEMENSAM = (
    "not flat vector, not clipart, not a pictogram, "
    "no solid color blocks, no uniform outlines, "
    "no text, no watermark, no photorealism, no 3d render"
)


def bygg_prompt(motiv: str, typ: str, färg_hex: str, färg_mörk: str,
                färg_namn: str, bakgrund_hex: str) -> str:
    """Bygger en picture-book-prompt runt ett motiv med kategoripalett.
    Håller sig under Recrafts 1000-teckensgräns."""

    # Typ-specifika tillägg (korta)
    if typ == "building":
        typ_rad = "weathered textures, imperfect brick and window lines, sense of place"
    elif typ == "human":
        typ_rad = "human warmth, minimal facial features, natural clothing wrinkles, real volume"
    elif typ == "group":
        typ_rad = "individuality per figure, natural postures, dimensional and warm"
    else:  # object
        typ_rad = "material character — visible grain, weight and texture"

    palett_rad = (
        f"palette: {färg_namn} {färg_hex} dominant with darker {färg_mörk} for linework, "
        f"warm off-white paper {bakgrund_hex}, muted earth tone accents only"
    )

    prompt = (
        f"subject: {motiv}. "
        f"{STIL_GEMENSAM}, {typ_rad}. "
        f"{palett_rad}. "
        f"{NEGATIV_GEMENSAM}."
    )

    # Recrafts gräns är 1000 tecken. Om vi är över (ovanligt långa motiv),
    # korta ner stilraden till minimum.
    if len(prompt) > 1000:
        kort_stil = "warm Scandinavian picture-book gouache, hand-painted with brush texture"
        kort_neg = "not flat vector, not clipart, no text, no watermark"
        prompt = (
            f"subject: {motiv}. "
            f"{kort_stil}, {typ_rad}. "
            f"{palett_rad}. "
            f"{kort_neg}."
        )
        # Sista utväg: trunkera motivet
        if len(prompt) > 1000:
            övrigt = len(prompt) - len(motiv)
            max_motiv = 1000 - övrigt - 10  # marginal
            prompt = prompt.replace(motiv, motiv[:max_motiv] + "...")

    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK-MOTIV för ID som inte ligger i MOTIV-katalogen
# ─────────────────────────────────────────────────────────────────────────────

def sök_leverantör_motiv(rid: str) -> str:
    """Letar substring-match i LEVERANTÖR_MOTIV."""
    rid_low = rid.lower()
    for nyckel, motiv in LEVERANTÖR_MOTIV.items():
        if nyckel in rid_low:
            return motiv
    return ""


def fallback_motiv(rid: str, kategori: str, namn: str, typ: str, rekvisita: str,
                   objekttyp: str, namn_en: str) -> str:
    """Bygg ett rimligt motiv när ID saknas i MOTIV."""

    # Försök hitta i underkataloger först
    if kategori == "Leverantörer":
        m = sök_leverantör_motiv(rid)
        if m:
            return m

    if kategori in ("Organisation", "Företagskultur"):
        if rid.lower() in GRUPP_MOTIV:
            return GRUPP_MOTIV[rid.lower()]

    if typ == "human":
        prop = rekvisita or "a single work prop"
        if kategori.startswith("Fastighets"):
            rollbeskrivning = "a property professional"
        elif kategori in ("Projektchef", "Arbetschef"):
            rollbeskrivning = "a confident project leader"
        elif kategori == "Politikkort":
            rollbeskrivning = "a thoughtful civic figure"
        elif kategori == "Personal":
            rollbeskrivning = "a professional staff member"
        else:
            rollbeskrivning = "a professional character"
        return f"{rollbeskrivning} standing in three-quarter view, holding {prop}"

    if typ == "group":
        prop = rekvisita or "a shared plan"
        if kategori == "Dialogkort":
            return f"two professionals facing each other in open conversation, sharing {prop}"
        return f"a small team of three gathered around {prop}, natural postures"

    if typ == "object":
        obj = objekttyp or "symbolic object"
        if namn_en and "building" not in namn_en.lower():
            return namn_en
        return f"a {obj} representing {namn.lower()}, painterly and characterful"

    if typ == "building":
        # Endast Instutition-kategorin ska hamna här enligt plan
        return f"a stately Swedish civic building representing {namn.lower()}, picture-book style"

    # Sista utväg
    return namn_en or f"a symbolic scene representing {namn.lower()}"


# ─────────────────────────────────────────────────────────────────────────────
# HUVUDLOGIK
# ─────────────────────────────────────────────────────────────────────────────

def main():
    xlsx_path = hitta_fil(1, ["bilder.xlsx", "bilder_v5_finjusterad_merged_v6.xlsx"])
    färg_path = hitta_fil(2, ["färgschema.xlsx"])
    print(f"Bilder: {xlsx_path}")
    print(f"Färger: {färg_path}")

    färger = läs_färgschema(färg_path)
    print(f"Laddade {len(färger)} färger: {', '.join(färger.keys())}")

    # Validera att alla kategorifärger finns
    saknade_färger = {f for f in KATEGORI_FÄRG.values() if f not in färger}
    if saknade_färger:
        print(f"⚠ Färger saknas i färgschemat: {saknade_färger}")
        return

    bakgrund_hex = färger.get("Åke Sundvall Rödgrå", {"hex": "#F9F2F2"})["hex"]

    # Backup av hela filen
    backup = skapa_backup(xlsx_path)
    print(f"Backup: {backup.name}")

    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb["Bilder"]
    src_kol, bak_kol = säkerställ_backupkolumn(ws)

    headers = [c.value for c in ws[1]]
    idx = {h: headers.index(h) + 1 for h in [
        "Unikt ID", "Kategori", "Namn (visas i spelet)",
        "Engelsk tolkning (prompt)", "Typ v6", "Rekvisita v6", "Objekttyp v6",
    ]}

    stats = {"motiv_katalog": 0, "fallback": 0, "okänd_kategori": 0,
             "inst_byggnad": 0, "totalt": 0}
    okända_kategorier = set()

    for row_num in range(2, ws.max_row + 1):
        rid = ws.cell(row=row_num, column=idx["Unikt ID"]).value
        if not rid:
            continue
        rid_str = str(rid).strip()
        kategori = str(ws.cell(row=row_num, column=idx["Kategori"]).value or "").strip()
        namn = str(ws.cell(row=row_num, column=idx["Namn (visas i spelet)"]).value or "").strip()
        namn_en = str(ws.cell(row=row_num, column=idx["Engelsk tolkning (prompt)"]).value or "").strip()
        typ = str(ws.cell(row=row_num, column=idx["Typ v6"]).value or "object").strip()
        rekvisita = str(ws.cell(row=row_num, column=idx["Rekvisita v6"]).value or "").strip()
        objekttyp = str(ws.cell(row=row_num, column=idx["Objekttyp v6"]).value or "").strip()

        # Hitta motiv
        motiv = MOTIV.get(rid_str.lower())
        if motiv:
            stats["motiv_katalog"] += 1
        else:
            motiv = fallback_motiv(rid_str, kategori, namn, typ, rekvisita, objekttyp, namn_en)
            stats["fallback"] += 1

        # Instutition ska behållas som picture-book-byggnad
        if kategori == "Instutition":
            typ = "building"
            stats["inst_byggnad"] += 1
        elif typ == "building":
            # För alla andra: om Typ v6 säger building, skriv om till object eftersom
            # vi INTE vill ha byggnader för dessa kort.
            typ = "object"

        # Färg
        färg_namn = KATEGORI_FÄRG.get(kategori)
        if not färg_namn:
            okända_kategorier.add(kategori)
            stats["okänd_kategori"] += 1
            färg_namn = "Åke Sundvall Grå"  # neutral fallback
        färg = färger[färg_namn]

        # Bygg prompt
        ny_prompt = bygg_prompt(
            motiv=motiv, typ=typ,
            färg_hex=färg["hex"], färg_mörk=färg["hex_mörk"],
            färg_namn=färg_namn, bakgrund_hex=bakgrund_hex,
        )

        # Backup av gammal prompt om inte redan gjord
        gammal = ws.cell(row=row_num, column=src_kol).value
        befintlig_backup = ws.cell(row=row_num, column=bak_kol).value
        if not befintlig_backup and gammal:
            ws.cell(row=row_num, column=bak_kol, value=gammal)

        ws.cell(row=row_num, column=src_kol, value=ny_prompt)
        stats["totalt"] += 1

    # Lägg in/uppdatera 'modell'-nyckeln i Inställningar
    ws_s = wb["Inställningar"]
    settings = {str(ws_s.cell(row=r, column=1).value).strip(): r
                for r in range(1, ws_s.max_row + 1) if ws_s.cell(row=r, column=1).value}
    if "modell" not in settings:
        next_row = ws_s.max_row + 1
        ws_s.cell(row=next_row, column=1, value="modell")
        ws_s.cell(row=next_row, column=2, value="recraft-v3")
    else:
        ws_s.cell(row=settings["modell"], column=2, value="recraft-v3")

    # Stäng av testläge så hela spelet genereras
    if "test_läge" in settings:
        ws_s.cell(row=settings["test_läge"], column=2, value="FALSE")

    wb.save(xlsx_path)

    print(f"\n✓ Skrev om {stats['totalt']} prompter")
    print(f"  varav motiv från katalog: {stats['motiv_katalog']}")
    print(f"  varav motiv från fallback: {stats['fallback']}")
    print(f"  varav Instutition-byggnader bevarade: {stats['inst_byggnad']}")
    if okända_kategorier:
        print(f"\n⚠ Okända kategorier (fick fallback-färg): {okända_kategorier}")
    print(f"\nInställningar: modell=recraft-v3, test_läge=FALSE")
    print(f"Kör nu: python generate_images_v6.py")


if __name__ == "__main__":
    main()

