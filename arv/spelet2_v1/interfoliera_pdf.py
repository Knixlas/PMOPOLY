"""
interfoliera_pdf.py v4
Hittar alla *_bildsida.pdf / *_textsida.pdf-par i angiven mapp och
skapar *_kombinerad.pdf med alternerande sidor:
  sida 1 = bild kort 1
  sida 2 = text kort 1
  sida 3 = bild kort 2
  sida 4 = text kort 2
  ...

Multipliceringen av antal exemplar sker när MASTER byggs:
  - exakt EN _kombinerad.pdf per korttyp skapas i Kombinerade\\
  - MASTER_alla_kort.pdf inkluderar varje korttyp `exemplar` gånger
    enligt PDF\\exemplar_map.json (som JSX-skriptet genererat från Excel)

Utskriftsinstruktion:
  1. Skriv ut MASTER_alla_kort.pdf – välj "Udda sidor" (1, 3, 5 …)
  2. Vänd bunten med bilden nedåt
  3. Skriv ut igen – välj "Jämna sidor" (2, 4, 6 …)

Anrop: python interfoliera_pdf.py "C:\\väg\\till\\PDF-mapp"
Kräver: pip install pypdf
"""

import sys
import os
import re
import json
from pypdf import PdfWriter, PdfReader


def las_exemplar_map(pdf_mapp: str) -> dict:
    """Läs PDF\\exemplar_map.json om den finns."""
    map_path = os.path.join(pdf_mapp, "exemplar_map.json")
    if not os.path.isfile(map_path):
        print(f"OBS: {map_path} saknas – alla kort får 1 exemplar i MASTER")
        return {}
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"FEL vid läsning av exemplar_map.json: {e}")
        return {}


def hamta_exemplar(exemplar_map: dict, basnamn: str) -> int:
    """
    Slå upp antal exemplar för en korttyp i exemplar_map.json.
    Testar flera varianter av nyckeln eftersom nyckeln kan vara
    basnamn, _bildsida eller _textsida.
    """
    if not exemplar_map:
        return 1

    # 1. Exakt match
    if basnamn in exemplar_map:
        return exemplar_map[basnamn]

    # 2. Case-insensitive
    low = basnamn.lower()
    for key, val in exemplar_map.items():
        if key.lower() == low:
            return val

    # 3. Med _bildsida/_textsida tillagt
    for suffix in ("_bildsida", "_textsida"):
        for key, val in exemplar_map.items():
            if key.lower() == (basnamn + suffix).lower():
                return val

    # 4. Med _bildsida/_textsida strippat från nycklar
    for key, val in exemplar_map.items():
        stripped = re.sub(r"_(bildsida|textsida)$", "", key, flags=re.IGNORECASE)
        if stripped.lower() == low:
            return val

    return 1  # fallback


def interfoliera(pdf_mapp: str) -> None:
    pdf_mapp = pdf_mapp.rstrip("\\/")

    if not os.path.isdir(pdf_mapp):
        print(f"FEL: Mappen finns inte: {pdf_mapp}")
        sys.exit(1)

    # Rensa gamla _kombinerad*.pdf och MASTER så vi inte får stale data
    ut_mapp = os.path.join(pdf_mapp, "Kombinerade")
    if os.path.isdir(ut_mapp):
        cleaned = 0
        for f in os.listdir(ut_mapp):
            if re.search(r"_kombinerad(?:_\d+)?\.pdf$", f, re.IGNORECASE) or f == "MASTER_alla_kort.pdf":
                try:
                    os.remove(os.path.join(ut_mapp, f))
                    cleaned += 1
                except Exception:
                    pass
        if cleaned > 0:
            print(f"Rensade {cleaned} gamla filer från {ut_mapp}")

    # Läs exemplar-mappen från JSX-skriptet
    exemplar_map = las_exemplar_map(pdf_mapp)
    if exemplar_map:
        print(f"Läste exemplar_map.json ({len(exemplar_map)} poster)")

    filer = os.listdir(pdf_mapp)

    # Hitta alla bildsida-PDF:er (med eller utan _N-suffix för exemplar)
    bildsidor = sorted(
        f for f in filer
        if re.search(r"_bildsida(?:_\d+)?\.pdf$", f, re.IGNORECASE)
    )

    if not bildsidor:
        print("Inga bildsida-PDF:er hittades – inget att interfoliera.")
        return

    logg = []
    ok = 0
    fel = 0

    os.makedirs(ut_mapp, exist_ok=True)

    # ── Steg 1: Skapa EN _kombinerad.pdf per korttyp (och per exemplar) ──
    for bildfil in bildsidor:
        m = re.match(r"^(.+)_bildsida(_\d+)?\.pdf$", bildfil, re.IGNORECASE)
        if not m:
            continue

        bas    = m.group(1)
        suffix = m.group(2) or ""  # t.ex. "_1", "_2" eller ""
        textfil = f"{bas}_textsida{suffix}.pdf"

        if textfil not in filer:
            logg.append(f"HOPPAR: {bildfil}  (saknar matchande {textfil})")
            continue

        bild_path = os.path.join(pdf_mapp, bildfil)
        text_path = os.path.join(pdf_mapp, textfil)
        ut_path = os.path.join(ut_mapp, f"{bas}_kombinerad{suffix}.pdf")

        try:
            bild_r = PdfReader(bild_path)
            text_r = PdfReader(text_path)
            writer = PdfWriter()

            n_bild = len(bild_r.pages)
            n_text = len(text_r.pages)

            if n_bild != n_text:
                logg.append(
                    f"VARNING: {bildfil} har {n_bild} sidor, "
                    f"{textfil} har {n_text} – interfolierar {min(n_bild, n_text)} par"
                )

            n = min(n_bild, n_text)
            for i in range(n):
                writer.add_page(bild_r.pages[i])
                writer.add_page(text_r.pages[i])

            with open(ut_path, "wb") as f:
                writer.write(f)

            msg = f"OK: {os.path.basename(ut_path)}  ({n} kortpar, {n * 2} sidor)"
            logg.append(msg)
            print(msg)
            ok += 1

        except Exception as e:
            msg = f"FEL: {bildfil}: {e}"
            logg.append(msg)
            print(msg)
            fel += 1

    # ── Steg 2: Bygg MASTER – varje korttyp `exemplar` gånger ───────────
    master_path = os.path.join(ut_mapp, "MASTER_alla_kort.pdf")
    fas_ordning = {"L_": 0, "PU": 1, "PL": 2, "GF": 3, "F_": 4}

    def fas_sort_key(filnamn):
        fn = os.path.basename(filnamn).upper()
        for prefix, prio in fas_ordning.items():
            if fn.startswith(prefix):
                return (prio, fn)
        return (9, fn)

    kombinerade = sorted(
        (os.path.join(ut_mapp, f) for f in os.listdir(ut_mapp)
         if re.search(r"_kombinerad(?:_\d+)?\.pdf$", f, re.IGNORECASE)),
        key=fas_sort_key,
    )

    if kombinerade:
        try:
            master = PdfWriter()
            total_pages = 0
            master_logg = []

            for komb_path in kombinerade:
                filnamn = os.path.basename(komb_path)
                # Ta bort _kombinerad(_N).pdf för att få basnamnet.
                # Suffixet _N behålls i basnamnet så uppslaget i
                # exemplar_map.json kan skilja olika exemplar åt.
                m = re.match(r"^(.+)_kombinerad(_\d+)?\.pdf$", filnamn, re.IGNORECASE)
                if m:
                    basnamn = m.group(1) + (m.group(2) or "")
                else:
                    basnamn = filnamn.replace(".pdf", "")

                exemplar = hamta_exemplar(exemplar_map, basnamn)

                reader = PdfReader(komb_path)
                sidor = list(reader.pages)

                # Lägg in samma PDF `exemplar` gånger
                for _ in range(exemplar):
                    for page in sidor:
                        master.add_page(page)
                    total_pages += len(sidor)

                master_logg.append(
                    f"  {filnamn}: x{exemplar} "
                    f"({len(sidor)} sidor styck, {len(sidor) * exemplar} totalt)"
                )

            with open(master_path, "wb") as f:
                master.write(f)

            msg = (f"\nMASTER: {os.path.basename(master_path)}  "
                   f"({len(kombinerade)} korttyper, {total_pages} sidor totalt)")
            logg.append(msg)
            logg.extend(master_logg)
            print(msg)
            for rad in master_logg:
                print(rad)
        except Exception as e:
            msg = f"\nFEL vid master-PDF: {e}"
            logg.append(msg)
            print(msg)
    else:
        logg.append("\nIngen master-PDF skapad (inga kombinerade filer)")

    # Sammanfattning
    summary = f"\nKlart: {ok} kombinerade PDF:er skapade, {fel} fel."
    logg.append(summary)
    print(summary)

    # Loggfil i SPELET 2\loggar\ (skapa mappen om den inte finns)
    spelet_rot = os.path.dirname(pdf_mapp.rstrip("\\/"))
    loggar_mapp = os.path.join(spelet_rot, "loggar")
    os.makedirs(loggar_mapp, exist_ok=True)
    logg_path = os.path.join(loggar_mapp, "interfoliering_logg.txt")
    with open(logg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(logg))

    print(f"Logg: {logg_path}")


if __name__ == "__main__":
    mapp = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    interfoliera(mapp)

