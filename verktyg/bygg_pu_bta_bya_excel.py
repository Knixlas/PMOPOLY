"""Bygg kortdata/PU_BTA.xlsx och kortdata/PU_BYA.xlsx ur det tryckta spelet.

BTA- och BYA-minneskort (klass A–D), Skede 1 Projektutveckling. Korttyperna är identiska
utom typ (BTA/BYA), rubrikord i tabellen och klassgränser.

Källor per korttyp:
  - arv/spelet2_v1/1. Projektutveckling/<typ>.csv   (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/<typ>_tryckeri.txt              (text utläst ur tryckfilen, 2 rader per kort:
                                                     rad 1 = bildsida med minnestext och klasstabell,
                                                     rad 2 = textsida '<typ>  Klass <X>')

Klasstabellen (A–D med kvm-intervall) står likadan på alla fyra korten och är alltså mallens fasta
text, inte ett datafält per kort. CSV-kolumnen Kvm jämförs mot tabellraden för kortets klass.
Tryckets värde gäller: avvikelser läggs i KORRIGERINGAR nedan och dokumenteras i Excel.

Kör:  python3 verktyg/bygg_pu_bta_bya_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

# (korttyp, klass, csv-kolumn) -> (värde i CSV, tryckt värde). Tryckets värde används i Excel.
KORRIGERINGAR = {
    ("PU_BYA", "A", "Kvm"): ("500-4000", "0-4000"),
}

PRODUKTION_KOLUMNER = ["@bildsida", "@textsida", "fill_color", "line_color", "skede_color",
                       "bakskede", "bakgrund_color", "ordning_bild", "ordning_text"]

TYPER = {
    "PU_BTA": {"typ": "BTA", "tabellord": "bruttototalarea", "benamning": "bruttoarea (BTA)",
               "tryck_andrad": "2026-04-27 19:29 UTC", "csv_datum": "2026-04-27 19:31:52 UTC"},
    "PU_BYA": {"typ": "BYA", "tabellord": "byggnadsarea", "benamning": "byggnadsarea (BYA)",
               "tryck_andrad": "2026-04-27 19:45 UTC", "csv_datum": "2026-04-27 20:27:27 UTC"},
}


def kort_kolumner(typ):
    return [
        ("Kort-id", None, False, "Löpnummer 1–4 i tryckordning"),
        ("Typ", "Typ", True, f"Står på båda sidor: {typ}"),
        ("Klass", "Klass", True, "Stor bokstav på bildsidan och 'Klass X' på textsidan"),
        (f"Klassintervall {typ} (kvm)", "Kvm", True,
         "Kortets rad i klasstabellen (tabellen står i sin helhet på varje kort, tryckt som '<intervall> kvm')"),
        ("ID", "ID", False, "Ej tryckt — internt id"),
        ("Antal exemplar", None, False, "Antal tryckta exemplar per kort (utskrift_config '_kombinerad': 4)"),
    ]


def malltext(typ, tabellord, tabell):
    return [
        ("Bildsida", "Rubrik", f"{typ} MINNESKORT"),
        ("Bildsida", "Rubrik", f"DIN TOTALA {typ}"),
        ("Bildsida", "Regel", "BEHÅLL KORTET SOM REFERENS"),
        ("Bildsida", "Regeltext", f"Summera {typ} från alla projekt som du har med till planeringsfasen. "
                                  "Läs av klass i tabellen nedan. Behåll kortet som referens."),
        ("Bildsida", "Tabellrubrik", f"KLASS · {tabellord}"),
        ("Bildsida", "Tabell", " · ".join(f"{k} {v} kvm" for k, v in tabell.items())),
        ("Bildsida", "Datafält", "Klassbokstav (från CSV 'Klass')"),
        ("Textsida", "Etiketter", f"{typ} (från CSV 'Typ') · Klass (före bokstaven från CSV 'Klass')"),
    ]


def las_tryck(namn, typ, tabellord):
    rader = [r for r in (TRYCKT_TEXT / f"{namn}_tryckeri.txt").read_text(encoding="utf-8").splitlines()
             if r.strip()]
    kort, tabeller = [], set()
    mall = (rf"{typ} MINNESKORT\s+DIN TOTALA {typ}\s+BEHÅLL KORTET SOM REFERENS\s+Summera\s+{typ}\s+från alla "
            r"projekt som du har\s+med till planeringsfasen\. Läs av klass i tabel -\s+len nedan\.\s+"
            rf"Behåll kortet som referens\.\s+KLASS {tabellord}\s+(.+?)\s+([A-D])")
    for bild, text in zip(rader[0::2], rader[1::2]):
        mb = re.fullmatch(mall, bild.strip())
        mt = re.fullmatch(r"(\S+)\s+Klass ([A-D])", text.strip())
        if not (mb and mt):
            sys.exit(f"{namn}: kunde inte tolka kort: {bild!r} / {text!r}")
        tab = mb.group(1)
        intervall = re.findall(r"(\d+-\d+|>\d+) kvm", tab)
        bokstaver = re.findall(r"\b([A-D])\b", tab)
        if sorted(bokstaver) != list("ABCD") or len(intervall) != 4:
            sys.exit(f"{namn}: kunde inte tolka klasstabellen: {tab!r}")
        # PDF:ens läsordning blandar ibland ihop raderna ('B A 5001-7000 kvm 500-5000 kvm').
        # Intervallen är stigande och icke-överlappande, så de ordnas efter undre gräns till A–D.
        undre = lambda s: int(s[1:]) + 1 if s.startswith(">") else int(s.split("-")[0])
        tabell = dict(zip("ABCD", sorted(intervall, key=undre)))
        tabeller.add(tuple(tabell.items()))
        kort.append({"Typ": mt.group(1), "Klass": mt.group(2), "_klass_bild": mb.group(2),
                     "Kvm": tabell[mt.group(2)]})
    if len(tabeller) != 1:
        sys.exit(f"{namn}: klasstabellen skiljer mellan korten: {tabeller}")
    return kort, dict(tabeller.pop())


def jamfor(namn, csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"{namn}: antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avv, korrigerade, anvanda = [], [], set()
    for r, t in zip(csv_rader, tryck):
        if t["_klass_bild"] != t["Klass"]:
            avv.append((r["ID"], "Klass (bildsida)", t["_klass_bild"], r["Klass"]))
        for falt in ("Typ", "Klass", "Kvm"):
            if normalisera(t[falt]) == normalisera(r[falt]):
                continue
            nyckel = (namn, r["Klass"], falt)
            if KORRIGERINGAR.get(nyckel) == (r[falt], t[falt]):
                korrigerade.append((r["ID"], falt, r[falt], t[falt]))
                anvanda.add(nyckel)
                r[falt] = t[falt]  # tryckets värde gäller
            else:
                avv.append((r["ID"], falt, t[falt], r[falt]))
    oanvanda = [k for k in KORRIGERINGAR if k[0] == namn and k not in anvanda]
    if oanvanda:
        sys.exit(f"{namn}: korrigering(ar) utan motsvarande avvikelse: {oanvanda}")
    return avv, korrigerade


def main():
    for namn, info in TYPER.items():
        typ = info["typ"]
        rader = las_csv(f"1. Projektutveckling/{namn}.csv", "Klass")
        tryck, tabell = las_tryck(namn, typ, info["tabellord"])
        avvikelser, korrigerade = jamfor(namn, rader, tryck)
        if avvikelser:
            for a in avvikelser:
                print("AVVIKELSE", namn, a)
            sys.exit(f"{namn}: CSV och tryck skiljer — åtgärda innan Excel byggs.")

        if korrigerade:
            korr_text = "; ".join(f"{i} {f}: CSV '{c}' → tryck '{t}'" for i, f, c, t in korrigerade)
            kontroll = (f"Typ, Klass och klassintervall jämförda kort för kort mot tryckfilen. "
                        f"{len(korrigerade)} avvikelse(r) CSV↔tryck, tryckets värde används i Excel: {korr_text}.")
        else:
            kontroll = "Typ, Klass och klassintervall jämförda kort för kort mot tryckfilen: 0 avvikelser."

        kalla = [
            ("Korttyp", f"{namn} — {typ}-minneskort (klass A–D för total {info['benamning']}), "
                        "Skede 1 Projektutveckling"),
            ("Antal kort", f"{len(rader)} unika (klass A–D), 4 exemplar vardera per spel "
                           f"(utskrift_config '{namn}_klass _kombinerad': 4) = {4 * len(rader)} kort per spel. "
                           "Tryckfilen innehåller 1 exemplar av varje (exemplar_map: 1)."),
            ("Format", f"58 × 88 mm, dubbelsidigt (bildsida + textsida) — {namn}_bildsida_layout.json"),
            ("Tryckfil", f"OneDrive: SPELET 2/PDF/Tryckbara/{namn}_tryckeri.pdf "
                         f"(senast ändrad {info['tryck_andrad']}, 8 sidor)"),
            ("Tryckfilens text", f"arv/tryckt_text/{namn}_tryckeri.txt (utläst via OneDrive, 8 sidor, "
                                 "rad 1 = bildsida, rad 2 = textsida per kort; att klassrubriken är textsidan "
                                 f"bekräftas av {namn}_textsida_temp.pdf)"),
            ("Datakälla", f"arv/spelet2_v1/1. Projektutveckling/{namn}.csv"),
            ("CSV-datum", f"{info['csv_datum']} — före tryckgränsen 22:14, men EFTER att tryckfilen "
                          f"skapades ({info['tryck_andrad']})"),
            ("Klasstabell", "Tabellen står likadan på alla fyra korten (mallens fasta text): "
                            + ", ".join(f"{k} {v} kvm" for k, v in tabell.items())
                            + ". PDF-textens läsordning blandar raderna; intervallen ordnas stigande till A–D."),
            ("Kontroll", kontroll),
        ]
        if korrigerade:
            kalla.append(("Korrigering", "Klass A:s undre gräns i CSV (500) stämmer inte med trycket (0). CSV:n "
                                         "ändrades efter att tryckfilen skapades; trycket är facit. "
                                         "Se KORRIGERINGAR i skriptet."))
        if typ == "BTA":
            kalla.append(("Anmärkning", "Tabellrubriken är tryckt 'bruttototalarea' (vanligen 'bruttoarea')."))
        kalla.append(("Byggd med", "verktyg/bygg_pu_bta_bya_excel.py"))

        ut = bygg_arbetsbok(
            filnamn=f"{namn}.xlsx",
            kort_kolumner=kort_kolumner(typ),
            rader=rader,
            namn_kolumn="ID",
            malltext=malltext(typ, info["tabellord"], tabell),
            produktion_kolumner=PRODUKTION_KOLUMNER,
            format_mm="58 × 88",
            exemplar=4,
            kalla=kalla,
        )
        print(f"Skrev {ut}: {len(rader)} kort × 4 exemplar, 0 avvikelser i speldata, "
              f"{len(korrigerade)} korrigerade mot tryck {korrigerade}")


if __name__ == "__main__":
    main()
