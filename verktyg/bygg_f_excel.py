"""Bygg kortdata/F_*.xlsx — Skede 3 (Förvaltning 2.1) — ur designfilerna i data/forvaltning_2-1/.

Korten är nya (inget tryck att jämföra mot). Kontrollen gäller i stället:
  - varje effektkod finns i FORVALTNING_KORTSPEC.md §1,
  - antal kort per lek stämmer med kortspecen,
  - unika ID:n, ingen tom rubrik/beskrivning, mekanik-kolumnerna finns.
Mekanik-kolumnerna (ID/Typ/Effekt/Synlig/Timing/Värde/Påverkar/Spår/Ändring) förs över orörda;
Rubrik/Beskrivning är korttexten.

Kör:  python verktyg/bygg_f_excel.py
"""
import csv
import re
import sys

from kortexcel import ROT, bygg_arbetsbok

KALLA = ROT / "data/forvaltning_2-1"
SPEC = ROT / "FORVALTNING_KORTSPEC.md"

# Koder som bara står i löptext i kortspecen (inga i dag)
EXTRA_KODER = set()

# (fil, xlsx, antal enligt spec, beskrivning, {kolumn: förklaring})
LEKAR = [
    ("F2-1_händelsekort.csv", "F_händelsekort.xlsx", 106, "Händelsekort — fyra typleker, ett kort per fastighet och kvartal",
     {"Typ": "Typlek: HYRESRÄTT, FÖRSKOLA, LOKAL, KONTOR", "Synlig": "ja = läggs öppet, nej = dold bricka"}),
    ("F2-1_kvartalskort.csv", "F_kvartalskort.xlsx", 50, "Kvartalskort — fyra typleker; kvartalets fokustyp avgör leken",
     {"Typ": "Typlek (fokustyp)"}),
    ("F2-1_nätverkskort.csv", "F_nätverkskort.xlsx", 83, "Nätverkskort — en gemensam lek på hand (max sex)",
     {"Timing": "När kortet får spelas"}),
    ("F2-1_omvärldskort.csv", "F_omvärldskort.xlsx", 36, "Omvärldskort — ett per kvartal, makro",
     {"Påverkar": "Spår eller typ som träffas"}),
    ("F2-1_DD.csv", "F_DD.xlsx", 36, "DD-kort — dolda vid övergång och köp", {}),
    ("F2-1_yieldkort.csv", "F_yieldkort.xlsx", 24, "Yieldkort — två spår, lägger yieldbanan (återanvänds från version 1 utan ±1,0)",
     {"Spår": "bostäder / kommersiellt", "Ändring": "Procentenheter som yielden flyttas"}),
    ("F2-1_FC.csv", "F_FC.xlsx", 6, "Fastighetschefer — dubbelsidiga (junior/senior), med typ", {}),
    ("F2-1_FS.csv", "F_FS.xlsx", 6, "Förvaltningsstöd — dubbelsidiga (junior/senior)", {}),
]

MEKANIK = {"ID", "Typ", "Effekt", "Synlig", "Timing", "Värde", "Påverkar", "Spår", "Ändring"}
TEXT = {"Rubrik", "Beskrivning", "Namn", "Junior", "Junior_styrka", "Junior_svaghet", "Senior"}


def koder_i_spec():
    s = SPEC.read_text(encoding="utf-8")
    koder = set()
    for cell in re.findall(r"^\| ((?:`[a-z_]+`(?: / )?)+) \|", s, re.M):
        koder |= set(re.findall(r"`([a-z_]+)`", cell))
    return koder | EXTRA_KODER


def main():
    koder = koder_i_spec()
    fel = []
    for fil, xlsx, antal, beskr, forkl in LEKAR:
        with open(KALLA / fil, encoding="utf-8", newline="") as f:
            rader = list(csv.DictReader(f, delimiter=";"))
        kol = list(rader[0].keys())

        if len(rader) != antal:
            fel.append(f"{fil}: {len(rader)} kort, spec säger {antal}")
        ids = [r["ID"] for r in rader]
        if len(set(ids)) != len(ids):
            fel.append(f"{fil}: dubbla ID:n")
        if "Effekt" in kol:
            okanda = sorted({r["Effekt"] for r in rader} - koder)
            if okanda:
                fel.append(f"{fil}: effektkoder saknas i kortspecen: {okanda}")
        for r in rader:
            for t in TEXT & set(kol):
                if not (r.get(t) or "").strip():
                    fel.append(f"{fil} {r['ID']}: tom {t}")

        kort_kolumner = [("Kort-id", None, False, "Löpnummer i leken")]
        for k in kol:
            if k in MEKANIK:
                kort_kolumner.append((k, k, k not in ("Effekt", "Synlig", "Timing"),
                                      "Mekanik — ändras bara genom design" + (f". {forkl[k]}" if k in forkl else "")))
        for k in kol:
            if k not in MEKANIK:
                kort_kolumner.append((k, k, True, "Korttext"))
        kort_kolumner.append(("Antal exemplar", None, False, "Per spel"))

        namn = "Rubrik" if "Rubrik" in kol else ("Namn" if "Namn" in kol else "ID")
        ut = bygg_arbetsbok(
            filnamn=xlsx,
            kort_kolumner=kort_kolumner,
            rader=rader,
            namn_kolumn=namn,
            malltext=[],
            produktion_kolumner=[],
            format_mm="ej bestämt",
            exemplar=1,
            langa_kolumner=tuple(k for k in kol if k in ("Beskrivning", "Junior_styrka", "Junior_svaghet", "Senior", "Junior",
                                                          "Värde", "Ändring")),  # med förtecken: behåll som text
            kalla=[
                ("Korttyp", beskr),
                ("Antal kort", f"{len(rader)} (kortspecen: {antal})"),
                ("Källa", f"data/forvaltning_2-1/{fil} — designfil för Förvaltning 2.1, ej tryckt"),
                ("Regler", "FORVALTNING_DESIGN_2-1.md (logik), FORVALTNING_KORTSPEC.md (effektkoder och fördelning)"),
                ("Kontroll", "Effektkoder mot kortspecen, antal, unika ID:n, ingen tom korttext"),
                ("Framöver", "Denna Excel är källan. Ändra korten här; designfilen i data/forvaltning_2-1/ utgår."),
                ("Byggd med", "verktyg/bygg_f_excel.py"),
            ],
        )
        print(f"Skrev {ut}: {len(rader)} kort")

    if fel:
        print("\nKONTROLLEN HITTADE FEL:")
        for f in fel:
            print(" ", f)
        sys.exit(1)
    print("Kontroll: OK")


if __name__ == "__main__":
    main()
