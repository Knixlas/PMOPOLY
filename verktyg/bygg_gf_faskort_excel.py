"""Bygg kortdata/GF_faskort.xlsx ur det tryckta spelet.

Faskort i Skede 2.2 Genomförande: 31 kort (PG_01_A … PG_08_C), ett eller flera per byggsteg 1–8.
Varje kort har fyra utfallsrader (Negativt, Neutralt, Positivt, Bonus); varje rad anger kompetens-
kraven i kolumnerna B, S och K samt rader effekt. Spelaren använder företagskultur (GF_kultur) för
att nå ett bättre utfall.

Källor:
  - arv/spelet2_v1/3. Genomförande/GF_faskort.csv   (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/GF_faskort_tryckeri.txt         (text utläst ur tryckfilen, 2 rader per kort:
                                                     rad 1 = bildsida, rad 2 = textsida)

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer som inte står i
korrigeringstabellerna nedan. I tabellerna gäller trycket.
Kör:  python3 verktyg/bygg_gf_faskort_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "GF_faskort_tryckeri.txt"

RADER = ["Negativt", "Bonus", "Neutralt", "Positivt"]          # ordningen i PDF-texten
EFFEKT = {"Negativt": "Effekt negativt", "Neutralt": "Effekt Neutralt",
          "Positivt": "Effekt positivt", "Bonus": "Effekt Bonus"}

# --- Korrigeringstabeller (trycket gäller) -------------------------------------------------------
#
# 1) Namnet får inte plats i mallens namnram på 7 kort: trycket visar en avkortad rubrik (ibland med
#    ett avstavningsstreck). Excel behåller CSV:ns fulla namn i "Namn" och visar det tryckta i
#    "Namn som tryckt". Fråga till användaren: ska den avkortade texten räknas som kortets namn?
NAMN_SOM_TRYCKT = {
    "PG_03_D": "Brandcellskrav vid verksamhets -",
    "PG_04_D": "Fasaddetaljer vid verksamhets -",
    "PG_05_C": "Beställaren vill ha smartare sys -",
    "PG_07_B": "Målningsarbetet underkänns vid",
    "PG_07_D": "Fel kvalitet på parkettgolven som",
    "PG_06_C": "Brandcellsgenomföringar under -",
    "PG_08_B": "Allmänna ytor inte färdigställda för",
}
# 2) Rubriken (byggsteget) på TEXTSIDAN är avkortad för två steg; bildsidan har hela rubriken.
RUBRIK_TEXTSIDA = {"INVÄNDIGA YTSKIKT": "INVÄNDIGA", "STOMKOMPLETTERING": "STOMKOMPLET -"}
# 3) "kostnad för kulturaktiviteter (Mkr)" är tryckt på varje kort men finns inte i CSV:n.
#    Värdet per byggsteg enligt trycket. OBS: steg 1 har 2 (övriga steg = stegnumret) —
#    fråga till användaren om det är avsiktligt.
KULTURKOSTNAD = {1: 2, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8}

KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–31 i tryckordning"),
    ("ID", "ID", True, "Kortnummer på textsidan, t.ex. PG_01_A"),
    ("Steg", "Steg", True, "Byggsteg 1–8 ('STEG n AV 8'; även på bildsidan)"),
    ("Rubrik (byggsteg)", "Rubrik", True, "Byggstegets namn på bildsidan; avkortat på textsidan för "
                                          "INVÄNDIGA YTSKIKT och STOMKOMPLETTERING"),
    ("Namn", "Namn", True, "Utmaningens namn enligt CSV — avkortat i trycket på 7 kort, se 'Namn som tryckt'"),
    ("Namn som tryckt", "Namn som tryckt", True,
     "Från tryckfilen (ej CSV): namnet som det faktiskt står på kortet"),
    ("Beskrivning", "Beskrivning", True, ""),
] + [(f"{rad} {k}", f"{rad} {k}", True,
      f"Kompetenskrav, utfallsrad {rad}, kolumn {k}" + (" ('—' på alla kort)" if rad == "Negativt" else
                                                        " (tomt = rutan är tom på kortet)"))
     for rad in ["Negativt", "Neutralt", "Positivt", "Bonus"] for k in "BSK"] + [
    (f"Effekt {rad.lower()}", EFFEKT[rad], True, f"Effekt vid utfall {rad}"
     + (" (tom på 3 kort)" if rad == "Neutralt" else ""))
    for rad in ["Negativt", "Neutralt", "Positivt", "Bonus"]] + [
    ("Kostnad kulturaktiviteter (Mkr)", "Kostnad kulturaktiviteter (Mkr)", True,
     "Från tryckfilen (ej CSV): 'kostnad för kulturaktiviteter (Mkr)'. Steg 1 = 2, övriga = stegnumret"),
    ("Antal exemplar", None, False, "Antal tryckta kort per spel (utskrift_config: 1)"),
]

PRODUKTION_KOLUMNER = ["@bild", "fill_color", "line_color", "skede_color", "bakskede",
                       "bakgrund_color", "ordning_bild", "ordning_text"]

MALLTEXT = [
    ("Bildsida", "Etiketter", "<Rubrik> · <Steg> · GF"),
    ("Textsida", "Sidhuvud", "GENOMFÖRANDE"),
    ("Textsida", "Etiketter", "STEG <n> AV 8 · GF · <Rubrik>"),
    ("Textsida", "Etiketter", "BOSTAD + 1 · ÖVRIGA BOSTÄDER"),
    ("Textsida", "Regel", "ANVÄND DIN FÖRETAGSKULTUR FÖR BÄTTRE UTFALL"),
    ("Textsida", "Etikett", "kostnad för kulturaktiviteter (Mkr) — värdet står inte i CSV:n, se kolumnen "
                            "'Kostnad kulturaktiviteter (Mkr)'"),
    ("Textsida", "Förklaring", "STA Stabilitet · KOM Kommunikation · SAM Samarbete · NOG Noggrannhet · "
                               "INN Innovation · ARB Arbetsmiljö  (OBS: 'ARB' i förklaringen, 'ABM' i värdena)"),
]

TEXT_MONSTER = re.compile(
    r"(?P<namn>.+?)  (?P<besk>.+?)  GENOMFÖRANDE  (?P<utfall>.+?)  STEG   (?P<steg>\d)   AV 8  "
    r"(?P<id>PG_\d\d_[A-Z])  GF   (?P<rubrik>.+?)  BOSTAD \+ 1   ÖVRIGA BOSTÄDER  ANVÄND DIN   "
    r"FÖRETAGSKULTUR   FÖR BÄTTRE UTFALL  kostnad för kultur-  aktiviteter \(Mkr\) (?P<kostnad>\d+)  "
    r"STA   Stabilitet  KOM   Kommunikation  SAM   Samarbete  NOG   Noggrannhet  INN   Innovation  "
    r"ARB   Arbetsmiljö")


def blank(v):
    return re.sub(r"\s+", " ", v or "").strip()


def forvantat_utfall(r):
    """Utfallsblocket som det står i PDF-texten: raderna i ordningen Negativt, Bonus, Neutralt, Positivt;
    inom varje rad kolumnerna S, K, B och sist effekten. Tomma rutor syns inte i texten."""
    delar = []
    for rad in RADER:
        delar += [r[f"{rad} {k}"] for k in "SKB"] + [r[EFFEKT[rad]]]
    return blank(" ".join(d for d in delar if (d or "").strip()))


def las_tryck():
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    if len(rader) % 2:
        sys.exit(f"{TRYCK_FIL.name}: udda antal sidor ({len(rader)})")
    kort = []
    for bild, text in zip(rader[0::2], rader[1::2]):
        mb = re.fullmatch(r"(.+?)  (\d)  GF", bild.strip())
        mt = TEXT_MONSTER.fullmatch(text.strip())
        if not (mb and mt):
            sys.exit(f"Kunde inte tolka kortet: {bild!r} / {text!r}")
        kort.append({"Rubrik": mb.group(1), "_steg_bild": mb.group(2), **mt.groupdict()})
    return kort


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avv = []
    for r, t in zip(csv_rader, tryck):
        i = r["ID"]
        for falt, tryckt, csv_v in [("ID", t["id"], r["ID"]), ("Steg (bildsida)", t["_steg_bild"], r["Steg"]),
                                    ("Steg (textsida)", t["steg"], r["Steg"]), ("Rubrik", t["Rubrik"], r["Rubrik"]),
                                    ("Beskrivning", t["besk"], r["Beskrivning"])]:
            if normalisera(tryckt) != normalisera(csv_v):
                avv.append((i, falt, tryckt, csv_v))
        if t["rubrik"] != RUBRIK_TEXTSIDA.get(r["Rubrik"], r["Rubrik"]):
            avv.append((i, "Rubrik (textsida)", t["rubrik"], r["Rubrik"]))
        if t["namn"] != NAMN_SOM_TRYCKT.get(i, r["Namn"]):
            avv.append((i, "Namn", t["namn"], r["Namn"]))
        if i in NAMN_SOM_TRYCKT and not r["Namn"].startswith(t["namn"].rstrip(" -")):
            avv.append((i, "Namn (avkortning)", t["namn"], r["Namn"]))
        if int(t["kostnad"]) != KULTURKOSTNAD[int(r["Steg"])]:
            avv.append((i, "Kostnad kulturaktiviteter", t["kostnad"], KULTURKOSTNAD[int(r["Steg"])]))
        if blank(t["utfall"]) != forvantat_utfall(r):
            avv.append((i, "Utfall", blank(t["utfall"]), forvantat_utfall(r)))
    return avv


def main():
    rader = las_csv("3. Genomförande/GF_faskort.csv", "ID")
    avvikelser = jamfor(rader, las_tryck())
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda innan Excel byggs.")

    # Tryckta värden som saknas i CSV:n (korrigeringstabellerna ovan) läggs till raderna.
    for r in rader:
        r["Namn som tryckt"] = NAMN_SOM_TRYCKT.get(r["ID"], r["Namn"])
        r["Kostnad kulturaktiviteter (Mkr)"] = str(KULTURKOSTNAD[int(r["Steg"])])

    ut = bygg_arbetsbok(
        filnamn="GF_faskort.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Namn",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="88 × 88",
        exemplar=1,
        langa_kolumner=("Namn", "Namn som tryckt", "Beskrivning"),
        kalla=[
            ("Korttyp", "GF_faskort — faskort (utmaningar per byggsteg), Skede 2.2 Genomförande"),
            ("Antal kort", f"{len(rader)} unika, 1 exemplar vardera per spel"),
            ("Format", "88 × 88 mm, dubbelsidigt (bildsida + textsida) — "
                       "_tryckeri_temp/GF_faskort_bildsida_layout.json"),
            ("Tryckfil", "OneDrive: SPELET 2/PDF/Tryckbara/GF_faskort_tryckeri.pdf"),
            ("Tryckfilens text", f"arv/tryckt_text/GF_faskort_tryckeri.txt (utläst via OneDrive, "
                                 f"{2 * len(rader)} sidor)"),
            ("Datakälla", "arv/spelet2_v1/3. Genomförande/GF_faskort.csv ('—' = U+2014 i Negativt B/S/K, "
                          "återställt från cp1252 0x97, se MANIFEST_csv.md)"),
            ("CSV-datum", "2026-04-26 13:31 — före tryck"),
            ("Kontroll", "ID, Steg (båda sidor), Rubrik, Beskrivning och hela utfallsblocket (alla B/S/K-krav "
                         "och effekter, i PDF-textens ordning Negativt–Bonus–Neutralt–Positivt, S–K–B–effekt) "
                         "jämförda kort för kort mot tryckfilen: 0 avvikelser i speldata."),
            ("Avvikelse: namn", "Namnet är avkortat i trycket på 7 kort (texten får inte plats i ramen): "
                                + "; ".join(f"{k}: '{v}'" for k, v in NAMN_SOM_TRYCKT.items())
                                + ". 'Namn' = CSV:ns fulla namn, 'Namn som tryckt' = trycket."),
            ("Avvikelse: rubrik", "Textsidans stegrubrik är avkortad: INVÄNDIGA YTSKIKT → 'INVÄNDIGA', "
                                  "STOMKOMPLETTERING → 'STOMKOMPLET -'. Bildsidan har hela rubriken."),
            ("Tryckt men ej i CSV", "'kostnad för kulturaktiviteter (Mkr)': steg 1 = 2, steg 2–8 = stegnumret. "
                                    "Tagen från trycket (kolumnen 'Kostnad kulturaktiviteter (Mkr)')."),
            ("Mall", "Förklaringsrutan på textsidan skriver 'ARB Arbetsmiljö' medan värdena använder 'ABM' "
                     "(GF_kultur skriver 'ABM Arbetsmiljö')."),
            ("B/S/K", "Bostad / Special / Komplex — tidigare indelning, samma logik (bekräftat av användaren)."),
            ("Kulturkostnad", "Steg 1 = 2 Mkr, steg 2–8 = stegnumret. Avsiktligt: 'andra chans' till samma kostnad "
                              "när man förstått logiken (bekräftat av användaren)."),
            ("Namn", "De fulla namnen i kolumnen Namn är de rätta; 'Namn som tryckt' visar tryckets avkortning."),
            ("Byggd med", "verktyg/bygg_gf_faskort_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser utöver korrigeringstabellerna")


if __name__ == "__main__":
    main()
