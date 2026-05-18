"""Load all game data from CSV/XLSX files."""
import csv
import json
import os
from typing import List, Dict, Tuple
from config import DATA_DIR, data_path
from models import (
    Project, PolitikDialogCard, SpecialCard, PlanningEventCard,
    Supplier, Organisation,
    PhaseCard, ExternalSupport, PenaltyCard, Staff, WorldEvent,
    ManagementEvent, DDCard, BYA_CLASSES, BTA_CLASSES,
)
import models


def detect_encoding(filepath: str) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(500)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "latin-1"


def read_csv(filepath: str) -> List[dict]:
    enc = detect_encoding(filepath)
    with open(filepath, "r", encoding=enc) as f:
        reader = csv.DictReader(f, delimiter=";")
        return list(reader)


def safe_int(val, default=0) -> int:
    if not val or str(val).strip() == "":
        return default
    try:
        return int(float(str(val).replace(",", ".").strip()))
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0) -> float:
    if not val or str(val).strip() == "":
        return default
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return default


def safe_str(val, default="") -> str:
    if val is None:
        return default
    return str(val).strip()


# ── Projects ──

def load_projects() -> Dict[str, List[Project]]:
    """Load projects grouped by type."""
    rows = read_csv(data_path("projekt"))
    stacks: Dict[str, List[Project]] = {}
    counters: Dict[str, int] = {}

    supplier_cols = [
        "MARK", "HUSUNDERBYGGNAD", "STOMME", "YTTERTAK", "FASADER",
        "STOMKOMPLETTERING", "INV YTSKIKT", "INSTALLATIONER", "GEMENSAMMA ARBETEN"
    ]

    for row in rows:
        typ = safe_str(row.get("Typ"))
        if not typ:
            continue
        forekomst = safe_int(row.get("Förekomst", row.get("F\x94rekomst")), 1)
        namn = safe_str(row.get("Namn"))

        supplier_reqs = {}
        for col in supplier_cols:
            val = safe_str(row.get(col))
            if val:
                supplier_reqs[col] = val

        for i in range(forekomst):
            counters[typ] = counters.get(typ, 0) + 1
            pid = f"{typ[:3].upper()}-{counters[typ]}"
            p = Project(
                id=pid, namn=namn, typ=typ, forekomst=forekomst,
                kostnad=safe_int(row.get("Kostnad")),
                formfaktor=safe_int(row.get("Formfaktor")),
                bta=safe_int(row.get("BTA")),
                anskaffning=safe_int(row.get("Anskaffning")),
                marknadsvarde=safe_int(row.get("Marknadsvärde", row.get("Marknadsv\x84rde"))),
                rorlig_intakt=safe_str(row.get("Rörligt marknadsvärde", row.get("R\x94rligt marknadsv\x84rde")), "D6"),
                kvalitet=safe_int(row.get("Kvalitet")),
                hallbarhet=safe_int(row.get("Hållbarhet", row.get("H\x86llbarhet"))),
                tid=safe_int(row.get("Tid")),
                riskbuffert=safe_int(row.get("Riskbuffert")),
                antal_krav=safe_int(row.get("Antal krav")),
                namndbeslut=safe_int(row.get("Nämndbeslut", row.get("N\x84mndbeslut")), 1),
                energiklass=safe_str(row.get("Energiklass"), "C"),
                driftnetto=safe_float(row.get("Driftnetto")),
                beskrivning=safe_str(row.get("Beskrivning")),
                supplier_reqs=supplier_reqs,
                led=safe_int(row.get("STA", row.get("LED"))),
                kom=safe_int(row.get("KOM")),
                sam=safe_int(row.get("SAM")),
                pro=safe_int(row.get("NOG", row.get("PRO"))),
                abm=safe_int(row.get("ABM")),
            )
            stacks.setdefault(typ, []).append(p)

    # Shuffle each stack
    import random
    for stack in stacks.values():
        random.shuffle(stack)

    return stacks


# ── Förvaltning 2.0: FC/FS-arketyper (separata kortlekar) ──

def load_f2_fc_arketyper() -> List[dict]:
    """Läs F2_FC_personal.csv (6 fastighetschef-arketyper med passiva egenskaper).

    Kolumner: Roll, ID, Namn, Specialisering, Kapacitet_proj, Lön_Mkr_per_kv,
    Förhandling (+3/-1/+1/0), Motstånd_konsekvens (+3/-1/+2/0), Specialeffekt, Not.
    """
    fp = os.path.join(DATA_DIR, "4_forvaltning_v2", "F2_FC_personal.csv")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    out = []
    for r in rows:
        nid = safe_str(r.get("ID"))
        if not nid:
            continue
        out.append({
            "roll": "FC",
            "id": nid,
            "namn": safe_str(r.get("Namn")),
            "specialisering": safe_str(r.get("Specialisering")),
            "kapacitet": safe_int(r.get("Kapacitet_proj")),
            "lon": safe_float(r.get("Lön_Mkr_per_kv")),
            "forhandling": safe_str(r.get("Förhandling")),
            "motstand_konsekvens": safe_str(r.get("Motstånd_konsekvens")),
            "specialeffekt": safe_str(r.get("Specialeffekt")),
            "not": safe_str(r.get("Not")),
        })
    return out


def load_f2_fs_arketyper() -> List[dict]:
    """Läs F2_FS_personal.csv (4 fastighetsspecialist-arketyper med taktiska egenskaper).

    Kolumner: Roll, ID, Namn, Specialisering, Lön_Mkr_per_kv, Effekt_beskrivning, Not.
    """
    fp = os.path.join(DATA_DIR, "4_forvaltning_v2", "F2_FS_personal.csv")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    out = []
    for r in rows:
        nid = safe_str(r.get("ID"))
        if not nid:
            continue
        out.append({
            "roll": "FS",
            "id": nid,
            "namn": safe_str(r.get("Namn")),
            "specialisering": safe_str(r.get("Specialisering")),
            "lon": safe_float(r.get("Lön_Mkr_per_kv")),
            "effekt_beskrivning": safe_str(r.get("Effekt_beskrivning")),
            "not": safe_str(r.get("Not")),
        })
    return out


def _parse_f2_modifier(s: str) -> int:
    """Parsea F2-modifier-sträng ('+3', '-1', '0', '+2') till int. 0 vid fel."""
    if not s:
        return 0
    s = s.strip()
    try:
        return int(s.replace("+", "").replace(" ", ""))
    except ValueError:
        return 0


def load_f2_dd() -> List[dict]:
    """Läs F2_DD.csv (10 DD-kort). Effekt_Mkr tolkas som DN-modifier i Mkr
    (positiv = dolt + DN, negativ = dolt − DN). Typ ('Kostnad'/'Intäkt') ger
    färg i UI:n."""
    fp = os.path.join(DATA_DIR, "4_forvaltning_v2", "F2_DD.csv")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    out = []
    for r in rows:
        nid = safe_str(r.get("ID"))
        if not nid:
            continue
        out.append({
            "id": nid,
            "typ": safe_str(r.get("Typ")),  # 'Kostnad' eller 'Intäkt'
            "rubrik": safe_str(r.get("Rubrik")),
            "effekt_mkr": safe_float(r.get("Effekt_Mkr")),
            "beskrivning": safe_str(r.get("Beskrivning")),
        })
    return out


def load_f2_handelsekort() -> List[dict]:
    """Läs F2_händelsekort.csv (28 typkort + 3 stoppkort).

    Effekt-kolumnen kan vara tom på rader där användaren inte fyllt i — då
    härleder vi värdet från är_*-flaggorna eller fill_color så spelets mekanik
    fungerar oavsett:
      är_varningskort=ja  → 'varning'
      är_energi_varning=ja → 'energivarning'
      är_förkjöpsrätt=ja  → 'förköpsrätt'
      är_stoppkort=ja     → 'stoppkort'
      annars (fill_color grön) → 'pluskort'
      annars (fill_color röd)  → 'minuskort'
    """
    fp = os.path.join(DATA_DIR, "4_forvaltning_v2", "F2_händelsekort.csv")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    out = []
    for r in rows:
        nid = safe_str(r.get("ID"))
        if not nid:
            continue
        effekt = safe_str(r.get("Effekt")).lower().strip()
        # Härleda effekt om tom
        if not effekt:
            if safe_str(r.get("Är_stoppkort", r.get("är_stoppkort"))).lower() == "ja":
                effekt = "stoppkort"
            elif safe_str(r.get("Är_förkjöpsrätt", r.get("är_förkjöpsrätt"))).lower() == "ja":
                effekt = "förköpsrätt"
            elif safe_str(r.get("Är_energi_varning", r.get("är_energi_varning"))).lower() == "ja":
                effekt = "energivarning"
            elif safe_str(r.get("Är_varningskort", r.get("är_varningskort"))).lower() == "ja":
                effekt = "varning"
            else:
                fill = safe_str(r.get("fill_color")).lower()
                if "1f5e2b" in fill or "5cc07a" in fill:
                    effekt = "pluskort"
                elif "9e968e" in fill or "ef5656" in fill:
                    effekt = "minuskort"
                else:
                    effekt = "minuskort"  # fallback
        out.append({
            "id": nid,
            "typ": safe_str(r.get("Typ")).upper(),
            "handelsetyp": safe_str(r.get("Händelsetyp")),
            "rubrik": safe_str(r.get("Rubrik")),
            "effekt": effekt,
            "beskrivning": safe_str(r.get("Beskrivning")),
            "ar_dolt": safe_str(r.get("Är_dolt", r.get("är_dolt"))).lower() == "ja",
        })
    return out


# Default-listor för FC/FS-personkort. Används när OneDrive-CSV:n bara har
# rubriker (som vid Q0 idag — du fyller i text senare). Varje kort har en
# kort 'effekt'-kod som backend-handlern kan matcha mot.
_DEFAULT_FC_PERSONKORT = [
    ("FCHK-01", "Energimässa",            "auto_energi",   "Spela istället för att slå för energiuppgradering — lyckas automatiskt."),
    ("FCHK-02", "Möte med kommunen",      "forh_plus2",    "+2 på nästa hyresförhandlingsslag."),
    ("FCHK-03", "Bra omdöme i pressen",   "blockera_kons", "Blockera nästa konsekvenskort som drabbar en av dina fastigheter."),
    ("FCHK-04", "Senior FC inhyrd",       "dn_plus1_q",    "+1 DN på en valfri fastighet under detta kvartal."),
    ("FCHK-05", "Förhandlingsteknik",     "forh_plus3",    "+3 på nästa hyresförhandlingsslag."),
    ("FCHK-06", "Nätverk i branschen",    "kika_kort",     "Titta på ett dolt kort hos en motståndare."),
    ("FCHK-07", "Strategiplan",           "flytta_kort",   "Flytta ett av dina dolda kort till en annan av dina fastigheter."),
    ("FCHK-08", "Diskussion med banken",  "ranta_minus1",  "-1 mkr räntekostnad detta kvartal."),
    ("FCHK-09", "Kassaflödesoptimering",  "cash_plus5",    "+5 mkr engångsbonus till kassan."),
    ("FCHK-10", "Bra avtal med leverantör","halverad_uppgr","Halverar kostnaden för nästa energiuppgradering."),
    ("FCHK-11", "Kontaktnät",             "forsta_val",    "Du får förstaval på nästa fastighet som dyker upp på marknaden."),
    ("FCHK-12", "Insider på stadshuset",  "byggratt_plus", "+1 byggrätt på en valfri fastighet (för framtida tillbyggnad)."),
    ("FCHK-13", "Lyckosam refinansiering","lan_minus10",   "Minska en fastighets lån med 10 Mkr (även räntekostnad sänks)."),
    ("FCHK-14", "Branschmässa",           "auto_energi",   "Auto-success på en energiuppgradering."),
    ("FCHK-15", "Forhandlingsdelegation", "forh_plus2",    "+2 på nästa hyresförhandlingsslag."),
    ("FCHK-16", "PR-kupp",                "dn_plus1_q",    "+1 DN denna runda på en valfri fastighet."),
    ("FCHK-17", "Markaffär",              "forsta_val",    "Förstaval på nästa marknadsfastighet."),
    ("FCHK-18", "Kassainjektion",         "cash_plus5",    "+5 mkr till kassan."),
    ("FCHK-19", "Bankrabatt",             "ranta_minus1",  "-1 mkr räntekostnad detta kvartal."),
    ("FCHK-20", "Reservplan",             "blockera_kons", "Blockera nästa konsekvenskort."),
]

_DEFAULT_FS_PERSONKORT = [
    ("FSHK-01", "Känningar i branschen",     "forh_plus2_efter","+2 på ett förhandlingsslag i efterhand."),
    ("FSHK-02", "Energirevision",            "konv_energivarn", "Konvertera 1 energivarning till en pluskort på samma fastighet."),
    ("FSHK-03", "Hyresgästrelation",         "annullera_minus", "Annullera nästa minuskort på en valfri fastighet."),
    ("FSHK-04", "Konsultarmé",               "skicka_tillb",    "Skicka tillbaka 1 konsekvenskort till leken."),
    ("FSHK-05", "Snabbjobbare",              "dn_plus1_q",      "+1 DN på fastighet med lägst Q i 1 kvartal."),
    ("FSHK-06", "Spaning",                   "kika_kort",       "Titta på ett dolt kort hos en motståndare."),
    ("FSHK-07", "Förebyggande underhåll",    "ta_bort_varning", "Ta bort 1 varningskort från en valfri fastighet."),
    ("FSHK-08", "Effektiv drift",            "ranta_minus1",    "-1 mkr räntekostnad detta kvartal."),
    ("FSHK-09", "Marknadsdata",              "byt_yield",       "Byt ett yield-kort i kön mot ett från toppen av leken."),
    ("FSHK-10", "Kvalitetslyft",             "dn_plus1_2q",     "+1 DN på en fastighet under 2 kvartal."),
    ("FSHK-11", "Hyresgästjuridik",          "blockera_hg",     "Blockera 1 hyresgäst-händelsekort."),
    ("FSHK-12", "Besiktningsexpert",         "ignorera_garanti","Ignorera nästa garantibesiktningskort."),
    ("FSHK-13", "Likviditetsstöd",           "cash_plus3",      "+3 mkr engångsbonus."),
    ("FSHK-14", "Underhållstajming",         "halverad_uppgr",  "Halverar kostnaden för nästa energiuppgradering."),
    ("FSHK-15", "Spaning2",                  "kika_kort",       "Titta på ett dolt kort hos en motståndare."),
    ("FSHK-16", "Förhandlingsbacking",       "forh_plus2_efter","+2 på senaste förhandlingsslag i efterhand."),
    ("FSHK-17", "Energiteknisk insikt",      "konv_energivarn", "Konvertera energivarning till pluskort."),
    ("FSHK-18", "Snabbreparation",           "annullera_minus", "Annullera nästa minuskort."),
    ("FSHK-19", "Driftekonomi",              "ranta_minus1",    "-1 mkr ränta."),
    ("FSHK-20", "Kvalitetspris",             "dn_plus1_q",      "+1 DN denna runda."),
]


def load_f2_personkort(roll: str) -> List[dict]:
    """Läs F2_FCkort.csv eller F2_FSkort.csv. Om CSV:n bara har platshållar-rader
    (mestadels tomma Rubrik/Beskrivning) faller vi tillbaka till default-listan
    så spelmekaniken fungerar redan idag.
    """
    filename = "F2_FCkort.csv" if roll == "FC" else "F2_FSkort.csv"
    fp = os.path.join(DATA_DIR, "4_forvaltning_v2", filename)
    csv_cards = []
    if os.path.exists(fp):
        rows = read_csv(fp)
        for r in rows:
            nid = safe_str(r.get("ID"))
            rubrik = safe_str(r.get("Rubrik"))
            besk = safe_str(r.get("Beskrivning"))
            if nid and rubrik:  # bara rader med ifylld rubrik
                # Använd 'effekt'-kod från beskrivning om kort namn matchar
                # default-listan, annars 'generic'
                effekt_code = "generic"
                default_match = next((d for d in (_DEFAULT_FC_PERSONKORT
                                                   if roll == "FC"
                                                   else _DEFAULT_FS_PERSONKORT)
                                       if d[0] == nid), None)
                if default_match:
                    effekt_code = default_match[2]
                csv_cards.append({
                    "id": nid, "roll": roll, "rubrik": rubrik,
                    "effekt": effekt_code, "beskrivning": besk,
                })
    # Om CSV har < 5 riktiga kort, använd default
    if len(csv_cards) < 5:
        defaults = _DEFAULT_FC_PERSONKORT if roll == "FC" else _DEFAULT_FS_PERSONKORT
        return [{"id": d[0], "roll": roll, "rubrik": d[1],
                 "effekt": d[2], "beskrivning": d[3]} for d in defaults]
    return csv_cards


def build_f2_staff_objects(fc_list: List[dict], fs_list: List[dict]) -> List[Staff]:
    """Bygg Staff-instanser från F2-arketyperna så befintliga hire-/turn-handlers
    kan använda dem oförändrat. Designdokets nyckelregler:
      - Inga lönekostnader (lon = 0.0)
      - Inga kapacitetstak (kapacitet = 999)
      - Egenskaperna (förh/motst-modifier som int, specialeffekt som text)

    Spelmekanik som tittar på arketyp-specifika egenskaper (t.ex. _energy_upgrade_modifier
    som ger +3 vid 'Tekniska experten') matchar på namn — F2-namnen bevaras.
    """
    out: List[Staff] = []
    for fc in fc_list:
        forh_mod = _parse_f2_modifier(fc.get("forhandling", ""))
        motst_mod = _parse_f2_modifier(fc.get("motstand_konsekvens", ""))
        # Lagra förhandlings- och motstånds-värdena i specialisering-textfältet
        # för synlighet i UI:n.
        spec = fc.get("specialisering", "")
        spec = f"{spec} · Förh {forh_mod:+d} / Motst {motst_mod:+d}"
        if fc.get("specialeffekt") and fc["specialeffekt"] != "-":
            spec += f" · {fc['specialeffekt']}"
        out.append(Staff(
            roll="FC",
            id=fc["id"],
            namn=fc["namn"],
            specialisering=spec,
            kapacitet=999,
            handelsemotstand=fc.get("motstand_konsekvens", ""),
            lon=0.0,
            forhandling="D6",  # baseline dice för bakåtkompatibel hyresförhandling
            f2_forh_modifier=forh_mod,
            f2_motstand_modifier=motst_mod,
        ))
    for fs in fs_list:
        spec = fs.get("specialisering", "")
        if fs.get("effekt_beskrivning"):
            spec += f" · {fs['effekt_beskrivning']}"
        out.append(Staff(
            roll="FS",
            id=fs["id"],
            namn=fs["namn"],
            specialisering=spec,
            kapacitet=999,
            handelsemotstand="",
            lon=0.0,
            forhandling="D6",
            f2_forh_modifier=0,
            f2_motstand_modifier=0,
        ))
    return out


# ── Förvaltning 2.0: berika projekt med Bas_DN / Lanebelopp / Rantekostnad ──

def enrich_projects_from_f2(stacks: Dict[str, List[Project]]) -> int:
    """Läs F2_fastighetskort.csv och fyll i bas_dn / lanebelopp / rantekostnad_kvartal
    på matchande projekt (per Namn). Returnerar antal projekt-instanser som berikats.

    Filen är optional — saknas den lämnas projekten orörda.
    """
    fp = os.path.join(DATA_DIR, "4_forvaltning_v2", "F2_fastighetskort.csv")
    if not os.path.exists(fp):
        return 0

    rows = read_csv(fp)
    by_name: Dict[str, dict] = {}
    for r in rows:
        namn = safe_str(r.get("Namn"))
        if namn:
            by_name[namn] = r

    enriched = 0
    for stack in stacks.values():
        for p in stack:
            r = by_name.get(p.namn)
            if not r:
                continue
            bd = safe_str(r.get("Bas_DN"))
            ln = safe_str(r.get("Lanebelopp"))
            rk = safe_str(r.get("Rantekostnad_kvartal"))
            if bd:
                p.bas_dn = safe_int(bd)
            if ln:
                p.lanebelopp = safe_int(ln)
            if rk:
                p.rantekostnad_kvartal = safe_int(rk)
            enriched += 1
    return enriched


# ── Politik/Dialog Cards ──

def load_politik_dialog() -> Tuple[List[PolitikDialogCard], List[PolitikDialogCard]]:
    """Läs PU_poldia.csv. Stödjer både gamla typer (Politik/Dialog) och nya
    sammanslagna typen HÄNDELSEKORT. Vid HÄNDELSEKORT läggs kortet i BÅDA leken
    så att brädets gamla 'politik' resp 'dialog'-rutor får dragbara kort.

    Kolumnnamnen för effekter har också ändrats från '2-10' till '2 till 10' osv.
    """
    rows = read_csv(data_path("poldia"))
    politik = []
    dialog = []

    # Mappning gamla -> nuvarande kolumnnamn för D20-effekter.
    effect_keys = [
        ("1", ["1"]),
        ("2-10", ["2-10", "2 till 10"]),
        ("11-15", ["11-15", "11 till 15"]),
        ("16-19", ["16-19", "16 till 19"]),
        ("20", ["20", "20+"]),
    ]

    for row in rows:
        typ = safe_str(row.get("Typ"))
        if not typ:
            continue
        effects = {}
        for canonical, aliases in effect_keys:
            for alias in aliases:
                val = safe_str(row.get(alias))
                if val:
                    effects[canonical] = val
                    break

        card = PolitikDialogCard(
            typ=typ, nr=safe_str(row.get("Nr")),
            rubrik=safe_str(row.get("Rubrik")),
            text=safe_str(row.get("Text")),
            effects=effects,
        )
        typ_lower = typ.lower()
        if "händelsekort" in typ_lower or "handelsekort" in typ_lower:
            # Ny sammanslagen typ – kortet ska vara dragbart från båda korttyperna
            # på brädet tills BOARD_SQUARES skrivits om till en gemensam korttyp.
            politik.append(card)
            dialog.append(card)
        elif typ_lower.startswith("politik"):
            politik.append(card)
        else:
            dialog.append(card)

    return politik, dialog


def load_special_cards() -> List[SpecialCard]:
    fp = data_path("poldia_spec")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    cards = []
    for row in rows:
        cards.append(SpecialCard(
            typ=safe_str(row.get("Typ")),
            rubrik=safe_str(row.get("Rubrik")),
            poverkar=safe_str(row.get("Påverkar", row.get("P\x86verkar"))),
            effekt=safe_str(row.get("Effekt")),
        ))
    return cards


# ── Suppliers ──

def load_suppliers() -> Dict[str, List[Supplier]]:
    rows = read_csv(data_path("leverantorer"))
    suppliers: Dict[str, List[Supplier]] = {}

    for row in rows:
        namn = safe_str(row.get("Namn"))
        if not namn:
            continue
        klass_priser = {
            "A": safe_int(row.get("Klass_A")),
            "B": safe_int(row.get("Klass_B")),
            "C": safe_int(row.get("Klass_C")),
            "D": safe_int(row.get("Klass_D")),
        }
        kompetenser = {
            "STA": safe_int(row.get("STA", row.get("LED"))),
            "KOM": safe_int(row.get("KOM")),
            "SAM": safe_int(row.get("SAM")),
            "NOG": safe_int(row.get("NOG", row.get("PRO"))),
            "INN": safe_int(row.get("INN")),
            "ABM": safe_int(row.get("ABM")),
        }
        s = Supplier(
            namn=namn, niva=safe_int(row.get("Nivå", row.get("Niv\x86")), 1),
            beskrivning=safe_str(row.get("Beskrivning")),
            beror_av=safe_str(row.get("Beror_av"), "BTA"),
            klass_priser=klass_priser,
            q=safe_int(row.get("Q")), h=safe_int(row.get("H")),
            t=safe_int(row.get("T_mån", row.get("T_m\x86n"))),
            erfarenhet=safe_int(row.get("erfarenhet")),
            kompetenser=kompetenser,
        )
        suppliers.setdefault(namn, []).append(s)

    # Sort each by level
    for key in suppliers:
        suppliers[key].sort(key=lambda x: x.niva)

    return suppliers


# ── Organisations ──

def load_organisations() -> Dict[str, List[Organisation]]:
    rows = read_csv(data_path("organisation"))
    orgs: Dict[str, List[Organisation]] = {}

    for row in rows:
        namn = safe_str(row.get("Namn"))
        if not namn:
            continue
        kompetenser = {
            "STA": safe_int(row.get("STA", row.get("LED"))),
            "KOM": safe_int(row.get("KOM")),
            "SAM": safe_int(row.get("SAM")),
            "NOG": safe_int(row.get("NOG", row.get("PRO"))),
            "INN": safe_int(row.get("INN")),
            "ABM": safe_int(row.get("ABM")),
        }
        o = Organisation(
            namn=namn, niva=safe_int(row.get("Nivå", row.get("Niv\x86")), 1),
            kostnad_mkr=safe_int(row.get("Kostnad_Mkr")),
            q=safe_int(row.get("Q")), h=safe_int(row.get("H")),
            t=safe_int(row.get("T_mån", row.get("T_m\x86n"))),
            erfarenhet=safe_int(row.get("erfa", row.get("erfarenhet"))),
            riskbuffert=safe_int(row.get("Riskbuffert")),
            kompetenser=kompetenser,
        )
        orgs.setdefault(namn, []).append(o)

    for key in list(orgs.keys()):
        orgs[key].sort(key=lambda x: x.niva)

    # Case-insensitive alias för att överbygga PLANNING_ORDER ("Stödfunktioner",
    # "Operativt team", "Marknadsteam", "Digitalisering") vs CSV-data
    # ("STÖDFUNKTIONER", "OPERATIVT TEAM", ...). Lägg in värdena under fler
    # varianter så att slot_name-lookup matchar oavsett skiftläge.
    aliases = {
        "STÖDFUNKTIONER": "Stödfunktioner",
        "OPERATIVT TEAM": "Operativt team",
        "MARKNADSTEAM": "Marknadsteam",
        "DIGITALISERING": "Digitalisering",
    }
    for csv_key, planning_key in aliases.items():
        if csv_key in orgs and planning_key not in orgs:
            orgs[planning_key] = orgs[csv_key]

    return orgs


# ── Planning Event Cards ──

def load_planning_events() -> Dict[str, List[PlanningEventCard]]:
    """Load planning event cards grouped by kort_id.

    Header-baserad lookup för att tåla nya kolumner från SPELET 2
    (t.ex. en 'Fas'-kolumn som la sig först 2026-04).
    """
    fp = data_path("handelsekort_pl")
    if not os.path.exists(fp):
        return {}

    rows = read_csv(fp)
    cards: Dict[str, List[PlanningEventCard]] = {}

    for row in rows:
        kid = safe_str(row.get("Kort_ID"))
        if not kid or kid.lower() == "tom":
            continue
        effects = [
            safe_str(row.get("Tröskel_1_5", row.get("Trskel_1_5", ""))),
            safe_str(row.get("Tröskel_6_17", row.get("Trskel_6_17", ""))),
            safe_str(row.get("Tröskel_18_20", row.get("Trskel_18_20", ""))),
            safe_str(row.get("Tröskel_21_plus", row.get("Trskel_21_plus", ""))),
        ]
        card = PlanningEventCard(
            kort_id=kid,
            id=safe_int(row.get("ID")),
            namn=safe_str(row.get("Namn")),
            typ=safe_str(row.get("Typ")),
            fas=safe_str(row.get("Fas")),
            svarighetsgrad=safe_str(row.get("Svårighetsgrad",
                                              row.get("Svarighetsgrad", ""))),
            beskrivning=safe_str(row.get("Beskrivning")),
            summering=safe_str(row.get("Summering")),
            trigger=safe_str(row.get("Trigger")) or "Alla",
            klassvillkor=safe_str(row.get("Klassvillkor")) or "Alla",
            effects=effects,
        )
        cards.setdefault(card.kort_id, []).append(card)

    return cards


def load_supplier_requirements() -> Dict[str, Dict[str, str]]:
    """Load project -> supplier requirement mappings from PU_projekt.csv.

    Returns: {supplier_type: {project_name: requirement_text}}
    """
    rows = read_csv(data_path("projekt"))
    supplier_cols = [
        "MARK", "HUSUNDERBYGGNAD", "STOMME", "YTTERTAK", "FASADER",
        "STOMKOMPLETTERING", "INV YTSKIKT", "INSTALLATIONER", "GEMENSAMMA ARBETEN"
    ]
    reqs: Dict[str, Dict[str, str]] = {t: {} for t in supplier_cols}

    for row in rows:
        namn = safe_str(row.get("Namn"))
        if not namn:
            continue
        for col in supplier_cols:
            val = safe_str(row.get(col))
            if val:
                reqs[col][namn] = val

    return reqs


# ── External Support (Kultur) ──

def load_external_support() -> List[ExternalSupport]:
    rows = read_csv(data_path("kultur"))
    cards = []
    for row in rows:
        namn = safe_str(row.get("Namn"))
        if not namn:
            continue
        kompetenser = {
            "STA": safe_int(row.get("STA", row.get("LED"))),
            "KOM": safe_int(row.get("KOM")),
            "SAM": safe_int(row.get("SAM")),
            "NOG": safe_int(row.get("NOG", row.get("PRO"))),
            "INN": safe_int(row.get("INN")),
            "ABM": safe_int(row.get("ABM")),
        }
        cards.append(ExternalSupport(
            id=safe_str(row.get("ID", "")),
            namn=namn, kompetenser=kompetenser,
        ))
    import random
    random.shuffle(cards)
    return cards


# ── Phase Cards (Faskort) ──

def load_phase_cards() -> Dict[int, List[PhaseCard]]:
    rows = read_csv(data_path("faskort"))
    cards: Dict[int, List[PhaseCard]] = {}

    for row in rows:
        pid = safe_str(row.get("ID"))
        steg = safe_int(row.get("Steg"))
        if not steg:
            continue

        levels = []
        for lvl_name, prefix in [("Negativt", "Negativt"), ("Neutralt", "Neutralt"),
                                   ("Positivt", "Positivt"), ("Bonus", "Bonus")]:
            levels.append({
                "name": lvl_name,
                "req_b": safe_str(row.get(f"{prefix} B")),
                "req_s": safe_str(row.get(f"{prefix} S")),
                "req_k": safe_str(row.get(f"{prefix} K")),
                "effect": safe_str(row.get(f"Effekt {lvl_name.lower()}", row.get(f"Effekt {prefix}"))),
            })

        card = PhaseCard(
            id=pid, steg=steg,
            namn=safe_str(row.get("Namn")),
            beskrivning=safe_str(row.get("Beskrivning")),
            levels=levels,
        )
        cards.setdefault(steg, []).append(card)

    return cards


# ── Penalty Cards ──

def _get_threshold_cols(row):
    """Find threshold column values, trying various encoding variants."""
    effects = []
    # Try multiple naming conventions for threshold columns
    suffix_sets = [
        ["_1_8", "_9_20", "_21_26", "_27_plus"],     # Current (D20_THRESHOLDS = [8,20,26,9999])
        ["_1_5", "_6_17", "_18_20", "_21_plus"],     # Legacy
        ["_1_8", "_9_15", "_16_21", "_22_plus"],     # Alternate
    ]
    prefixes = ["Troskel", "Tröskel", "Tr\xe4skel", "Tr\xf6skel"]
    for suffixes in suffix_sets:
        found = False
        for prefix in prefixes:
            val = safe_str(row.get(f"{prefix}{suffixes[0]}"))
            if val:
                found = True
                break
        if found:
            for suffix in suffixes:
                val = ""
                for prefix in prefixes:
                    val = safe_str(row.get(f"{prefix}{suffix}"))
                    if val:
                        break
                effects.append(val)
            break
    # Fallback: try any 4 Tröskel columns in order
    if not effects:
        for prefix in prefixes:
            cols = sorted([k for k in row.keys() if k.startswith(prefix)])
            if len(cols) >= 4:
                effects = [safe_str(row.get(c)) for c in cols[:4]]
                break
    return effects


def load_penalty_cards() -> Dict[str, List[PenaltyCard]]:
    rows = read_csv(data_path("konsekvenskort"))
    cards: Dict[str, List[PenaltyCard]] = {}
    for row in rows:
        typ = safe_str(row.get("Typ"))
        if not typ:
            continue
        effects = _get_threshold_cols(row)
        cards.setdefault(typ, []).append(PenaltyCard(
            typ=typ, nr=safe_str(row.get("Nr")),
            namn=safe_str(row.get("Namn")),
            effects=effects,
            energiklass_projekt=safe_int(row.get("Energiklass_projekt")),
        ))
    import random
    for pile in cards.values():
        random.shuffle(pile)
    return cards


def load_garanti_cards() -> Dict[str, List[PenaltyCard]]:
    rows = read_csv(data_path("garantibesiktning"))
    cards: Dict[str, List[PenaltyCard]] = {}
    for row in rows:
        typ = safe_str(row.get("Typ"))
        if not typ:
            continue
        effects = _get_threshold_cols(row)
        cards.setdefault(typ, []).append(PenaltyCard(
            typ=typ, nr=safe_str(row.get("Nr")),
            namn=safe_str(row.get("Namn")),
            effects=effects,
        ))
    import random
    for pile in cards.values():
        random.shuffle(pile)
    return cards


# ── Phase 4 Data ──

def load_staff() -> List[Staff]:
    rows = read_csv(data_path("personal"))
    staff = []
    for row in rows:
        # CSV-Roll är "FASTIGHETSCHEF"/"FASTIGHETSSKÖTARE", normalisera till
        # "FC"/"FS" som resten av koden förväntar sig (main.py-filter,
        # engine.py-display osv).
        raw_roll = safe_str(row.get("Roll")).upper()
        if raw_roll.startswith("FASTIGHETSCH"):
            roll = "FC"
        elif raw_roll.startswith("FASTIGHETSSK"):
            roll = "FS"
        else:
            roll = raw_roll
        staff.append(Staff(
            roll=roll,
            id=safe_str(row.get("ID")),
            namn=safe_str(row.get("Namn")),
            specialisering=safe_str(row.get("Specialisering")),
            kapacitet=safe_int(row.get("Kapacitet_proj"), 1),
            handelsemotstand=safe_str(row.get("Händelsemotstånd", row.get("H\x84ndelsemotst\x86nd"))),
            lon=safe_float(row.get("Lön_Mkr_per_kv", row.get("L\x94n_Mkr_per_kv"))),
            forhandling=safe_str(row.get("Förhandling", row.get("F\x94rhandling"))),
        ))
    return staff


def _parse_kompetenser(text: str) -> Dict[str, int]:
    """Parse competence string like 'LED:2, SAM:3' into dict."""
    result = {}
    if not text:
        return result
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            key, val = part.split(":", 1)
            result[key.strip().upper()] = safe_int(val.strip())
    return result


def _parse_namnd_bonus(not_text: str) -> int:
    """Extract namnd bonus from Not field, e.g. 'nämndbonus +3' → 3."""
    import re
    m = re.search(r'n[äa]mndbonus\s*\+?\s*(\d+)', not_text, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _parse_lindring(not_text: str) -> int:
    """Extract lindring bonus from Not field, e.g. 'Lindrar politikkort +2' → 2."""
    import re
    m = re.search(r'[Ll]indrar.*\+(\d+)', not_text)
    return int(m.group(1)) if m else 0


def _parse_erfarenhet(not_text: str) -> int:
    """Extract experience bonus from Not field, e.g. '+2 erfarenhet' → 2."""
    import re
    m = re.search(r'\+(\d+)\s*erfarenhet', not_text, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def load_pc_ac_staff() -> Dict[str, list]:
    """Load PC and AC candidates from PU_PL_personal.csv.

    Stödjer både gamla rollnamnen ('PC', 'AC') och de nya
    ('PROJEKTCHEF', 'ARBETSCHEF') från SPELET 2:s nuvarande filstruktur.
    """
    fp = data_path("pu_pl_personal")
    if not os.path.exists(fp):
        return {"PC": [], "AC": []}
    rows = read_csv(fp)
    result = {"PC": [], "AC": []}
    # Map both old and new role names to internal "PC" / "AC"
    ROLL_MAP = {
        "PC": "PC", "PROJEKTCHEF": "PC",
        "AC": "AC", "ARBETSCHEF": "AC",
    }
    for row in rows:
        roll_raw = safe_str(row.get("Roll")).upper()
        roll = ROLL_MAP.get(roll_raw)
        if roll is None:
            continue
        # Skip empty template rows (no ID)
        if not safe_str(row.get("ID")):
            continue
        beskrivning = safe_str(row.get("Beskrivning", row.get("Not", "")))

        kompetenser = {
            "STA": safe_int(row.get("STA", row.get("LED"))),
            "KOM": safe_int(row.get("KOM")),
            "SAM": safe_int(row.get("SAM")),
            "NOG": safe_int(row.get("NOG", row.get("PRO"))),
            "INN": safe_int(row.get("INN")),
            "ABM": safe_int(row.get("ABM")),
        }
        kompetenser = {k: v for k, v in kompetenser.items() if v > 0}

        entry = {
            "roll": roll,
            "id": safe_str(row.get("ID")),
            "namn": safe_str(row.get("Namn")),
            "specialisering": safe_str(row.get("Specialisering")),
            "handelsemotstand": safe_str(row.get("Händelsemotstand",
                                    row.get("Händelsemotstånd", ""))),
            "kompetenser": kompetenser,
            "not_text": beskrivning,
            "rb": safe_int(row.get("Rb")),
            "q_bonus": safe_int(row.get("Q")),
            "h_bonus": safe_int(row.get("H")),
            "t_bonus": safe_int(row.get("T")),
        }
        if roll == "PC":
            # Lindring slopas på PrC — istället används Erfarenhet som lindrar
            # alla händelsekort i Skede 1 (samma mekanik som AC i Skede 2-3).
            entry["erfarenhet"] = safe_int(row.get("Erfarenhet"))
            entry["namnd_bonus"] = safe_int(row.get("Nämnd", row.get("N\xe4mnd", 0)))
            entry["lon"] = 0  # PC cost handled differently now
        elif roll == "AC":
            entry["erfarenhet"] = safe_int(row.get("Erfarenhet"))
            entry["lon"] = 0  # AC cost handled differently now
        result[roll].append(entry)
    return result


def load_yield_cards() -> Dict[str, List[float]]:
    """Load yield change cards grouped by type (bostäder/kommersiellt)."""
    rows = read_csv(data_path("yield"))
    cards: Dict[str, List[float]] = {"bostader": [], "kommersiellt": []}
    for row in rows:
        titel = safe_str(row.get("Titel")).lower()
        # Ändring column may have % sign, e.g. "-1,50%"
        andring_str = safe_str(row.get("Ändring", row.get("\x84ndring", row.get("Ändring"))))
        andring_str = andring_str.replace("%", "").replace(",", ".").strip()
        try:
            andring = float(andring_str) if andring_str else 0.0
        except ValueError:
            andring = 0.0
        if "bost" in titel:
            cards["bostader"].append(andring)
        elif "kommersi" in titel:
            cards["kommersiellt"].append(andring)
    import random
    random.shuffle(cards["bostader"])
    random.shuffle(cards["kommersiellt"])
    return cards


def load_world_events() -> List[WorldEvent]:
    fp = data_path("omvarldskort")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    events = []
    for row in rows:
        events.append(WorldEvent(
            id=safe_str(row.get("ID")),
            rubrik=safe_str(row.get("Rubrik")),
            effekt_typ=safe_str(row.get("Effekt_typ")),
            effekt_mkr=safe_float(row.get("Effekt_Mkr")),
            poverkar=safe_str(row.get("Påverkar", row.get("P\x86verkar"))),
            beskrivning=safe_str(row.get("Beskrivning")),
        ))
    return events


def load_dd_cards() -> List[DDCard]:
    rows = read_csv(data_path("dd"))
    cards = []
    for row in rows:
        cards.append(DDCard(
            id=safe_str(row.get("ID")),
            typ=safe_str(row.get("Typ")),
            rubrik=safe_str(row.get("Rubrik")),
            effekt_mkr=safe_float(row.get("Effekt_Mkr")),
            beskrivning=safe_str(row.get("Beskrivning")),
        ))
    import random
    random.shuffle(cards)
    return cards


def load_mgmt_events() -> Dict[str, List[ManagementEvent]]:
    """Load management händelsekort grouped by type.

    Använder header-namn istf positionsindex så vi tål nya kolumner
    som SPELET 2 lägger till (t.ex. 'Händelsetyp' som infördes 2026-04).
    """
    fp = data_path("handelsekort_forv")
    if not os.path.exists(fp):
        return {}
    rows = read_csv(fp)
    cards: Dict[str, List[ManagementEvent]] = {}

    def _flt(val):
        s = safe_str(val).replace(",", ".")
        try:
            return float(s) if s else 0.0
        except (ValueError, TypeError):
            return 0.0

    for row in rows:
        rid = safe_str(row.get("ID"))
        if not rid:
            continue
        card = ManagementEvent(
            id=rid,
            typ=safe_str(row.get("Typ")),
            rubrik=safe_str(row.get("Rubrik")),
            effekt_mkr=_flt(row.get("Effekt_Mkr", row.get("Effekt", 0))),
            mildring_roll=safe_str(row.get("Mildring_roll")),
            mildring_spec=safe_str(row.get("Mildring_spec")),
            mildring_effekt_mkr=_flt(row.get("Mildring_effekt_Mkr",
                                              row.get("Mildring_effekt", 0))),
            trigger="Alla",
            beskrivning=safe_str(row.get("Beskrivning")),
        )
        cards.setdefault(card.typ, []).append(card)
    import random
    for pile in cards.values():
        random.shuffle(pile)
    return cards


# ── BYA/BTA Classification ──

def load_klass_table():
    """Load BYA/BTA class thresholds from CSV.

    CSV format: Klass;Typ;Kvm (e.g. "A;BTA;500-5000")
    Uses first set of 4 rows per type (BTA/BYA).
    """
    fp = data_path("btabya")
    if not os.path.exists(fp):
        models.BYA_CLASSES = [(0, 6000, "A"), (6001, 8000, "B"), (8001, 10000, "C"), (10001, 999999, "D")]
        models.BTA_CLASSES = [(0, 6000, "A"), (6001, 8000, "B"), (8001, 10000, "C"), (10001, 999999, "D")]
        return

    rows = read_csv(fp)
    bta_ranges = []
    bya_ranges = []
    bta_seen = set()
    bya_seen = set()

    for row in rows:
        klass = safe_str(row.get("Klass"))
        typ = safe_str(row.get("Typ")).upper()
        kvm_str = safe_str(row.get("Kvm"))
        if not klass or not kvm_str:
            continue

        # Only use first occurrence of each class per type
        if typ == "BTA" and klass not in bta_seen:
            bta_seen.add(klass)
            bta_ranges.append((klass, kvm_str))
        elif typ == "BYA" and klass not in bya_seen:
            bya_seen.add(klass)
            bya_ranges.append((klass, kvm_str))

    def parse_ranges(ranges):
        result = []
        for klass, range_str in ranges:
            range_str = range_str.replace(" ", "")
            if "-" in range_str and not range_str.startswith(">") and not range_str.startswith("<"):
                parts = range_str.split("-")
                try:
                    lo, hi = int(parts[0]), int(parts[1])
                    result.append((lo, hi, klass))
                except ValueError:
                    pass
            elif range_str.startswith(">"):
                try:
                    lo = int(range_str[1:]) + 1
                    result.append((lo, 999999, klass))
                except ValueError:
                    pass
            elif range_str.startswith("<"):
                try:
                    hi = int(range_str[1:])
                    result.append((0, hi, klass))
                except ValueError:
                    pass
        result.sort(key=lambda x: x[0])
        return result

    models.BTA_CLASSES = parse_ranges(bta_ranges) or [(0, 5000, "A"), (5001, 7000, "B"), (7001, 9000, "C"), (9001, 999999, "D")]
    models.BYA_CLASSES = parse_ranges(bya_ranges) or [(0, 6000, "A"), (6001, 8000, "B"), (8001, 10000, "C"), (10001, 999999, "D")]


# ── Puzzle Shapes ──

def load_shapes() -> Dict[str, List[List[int]]]:
    """Load polyomino shapes from shapes.json."""
    shapes_path = os.path.join(DATA_DIR, "shapes.json")
    if not os.path.exists(shapes_path):
        return {}
    with open(shapes_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Mark Expansion Pieces ──

def _generate_polyomino(n: int, rng=None) -> List[List[int]]:
    """Generate a random connected polyomino of n cells using random growth."""
    if rng is None:
        import random as rng
    cells = {(0, 0)}
    while len(cells) < n:
        # Find all neighbors of current cells
        neighbors = set()
        for r, c in cells:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nb = (r + dr, c + dc)
                if nb not in cells:
                    neighbors.add(nb)
        # Pick a random neighbor
        chosen = rng.choice(list(neighbors))
        cells.add(chosen)
    # Normalize to origin
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return sorted([r - min_r, c - min_c] for r, c in cells)


def load_mark_expansions() -> List[dict]:
    """Load mark expansion piece definitions from CSV.
    Each piece has: {id, cell_count, cells: [[r,c],...]}.
    Generates random polyomino shapes since images don't exist yet.
    """
    fp = data_path("markexpansion")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    import random
    rng = random.Random(42)  # Deterministic shapes
    pieces = []
    for i, row in enumerate(rows):
        n = safe_int(row.get("Antal rutor"), 3)
        pieces.append({
            "id": f"EXP-{i+1}",
            "cell_count": n,
            "cells": _generate_polyomino(n, rng),
        })
    rng.shuffle(pieces)
    return pieces


# ── Load All ──

class GameData:
    """Container for all loaded game data (read-only after init)."""

    def __init__(self):
        load_klass_table()
        self.projects = load_projects()
        # Förvaltning 2.0 – fyll i förtryckta lånevärden + Bas_DN på projekten.
        self.f2_enriched_count = enrich_projects_from_f2(self.projects)
        # Förvaltning 2.0 – FC/FS-arketyper. Råform och Staff-instanser.
        self.f2_fc_arketyper = load_f2_fc_arketyper()
        self.f2_fs_arketyper = load_f2_fs_arketyper()
        self.f2_staff_objects = build_f2_staff_objects(self.f2_fc_arketyper, self.f2_fs_arketyper)
        # F2-händelsekort per fastighet och FC/FS-personkort (default-lista om CSV tom).
        self.f2_handelsekort = load_f2_handelsekort()
        self.f2_fc_personkort = load_f2_personkort("FC")
        self.f2_fs_personkort = load_f2_personkort("FS")
        self.f2_dd_cards = load_f2_dd()
        self.politik, self.dialog = load_politik_dialog()
        self.special_cards = load_special_cards()
        self.suppliers = load_suppliers()
        self.organisations = load_organisations()
        self.planning_events = load_planning_events()
        self.supplier_requirements = load_supplier_requirements()
        self.external_support = load_external_support()
        self.phase_cards = load_phase_cards()
        self.penalty_cards = load_penalty_cards()
        self.garanti_cards = load_garanti_cards()
        self.staff = load_staff()
        _pc_ac = load_pc_ac_staff()
        self.pc_staff = _pc_ac["PC"]
        self.ac_staff = _pc_ac["AC"]
        self.yield_cards = load_yield_cards()
        self.world_events = load_world_events()
        self.dd_cards = load_dd_cards()
        self.mgmt_events = load_mgmt_events()
        self.shapes = load_shapes()
        self.mark_expansion_deck = load_mark_expansions()

        total_projects = sum(len(v) for v in self.projects.values())
        total_events = sum(len(v) for v in self.planning_events.values())
        total_phase_cards = sum(len(v) for v in self.phase_cards.values())
        total_penalty = sum(len(v) for v in self.penalty_cards.values())
        total_garanti = sum(len(v) for v in self.garanti_cards.values())
        total_mgmt = sum(len(v) for v in self.mgmt_events.values())
        total_yield = sum(len(v) for v in self.yield_cards.values())
        print(f"  Data loaded: {total_projects} projects "
              f"({self.f2_enriched_count} berikade via F2_fastighetskort, "
              f"F2: {len(self.f2_fc_arketyper)} FC + {len(self.f2_fs_arketyper)} FS-arketyper), "
              f"{len(self.politik)} politik, {len(self.dialog)} dialog, "
              f"{sum(len(v) for v in self.suppliers.values())} suppliers, "
              f"{sum(len(v) for v in self.organisations.values())} orgs, "
              f"{total_events} planning events, "
              f"{total_phase_cards} faskort, {len(self.external_support)} kulturkort, "
              f"{total_penalty} konsekvenskort, {total_garanti} garantikort, "
              f"{len(self.staff)} personal, {total_yield} yield, "
              f"{len(self.world_events)} omvärld, {len(self.dd_cards)} DD, "
              f"{total_mgmt} händelsekort, "
              f"{len(self.shapes)} shapes")
