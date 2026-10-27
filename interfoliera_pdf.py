"""
interfoliera_pdf.py
Hittar alla *_bildsida.pdf / *_textsida.pdf-par i angiven mapp och
skapar *_kombinerad.pdf med alternerande sidor:
  sida 1 = bild kort 1
  sida 2 = text kort 1
  sida 3 = bild kort 2
  sida 4 = text kort 2
  ...

Utskriftsinstruktion:
  1. Skriv ut *_kombinerad.pdf – välj "Udda sidor" (1, 3, 5 …)
  2. Vänd bunten med bilden nedåt
  3. Skriv ut igen – välj "Jämna sidor" (2, 4, 6 …)

Anrop: python interfoliera_pdf.py "C:\\väg\\till\\PDF-mapp"
Kräver: pip install pypdf
"""

import sys
import os
import re
from pypdf import PdfWriter, PdfReader


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

    for bildfil in bildsidor:
        m = re.match(r"^(.+)_bildsida(_\d+)?\.pdf$", bildfil, re.IGNORECASE)
        if not m:
            continue

        bas    = m.group(1)
        suffix = m.group(2) or ""
        textfil = f"{bas}_textsida{suffix}.pdf"

        if textfil not in filer:
            logg.append(f"HOPPAR: {bildfil}  (saknar matchande {textfil})")
            continue

        bild_path = os.path.join(pdf_mapp, bildfil)
        text_path = os.path.join(pdf_mapp, textfil)
        ut_mapp   = os.path.join(pdf_mapp, "Kombinerade")
        os.makedirs(ut_mapp, exist_ok=True)
        ut_path   = os.path.join(ut_mapp, f"{bas}_kombinerad{suffix}.pdf")

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

    # ── Master-PDF: alla kombinerade i en enda fil ──────────────────────
    # Ordning: PU_ → PL_ → GF_ → F_ (per fas), sedan alfabetiskt inom fas
    master_path = os.path.join(ut_mapp, "MASTER_alla_kort.pdf")
    fas_ordning = {"PU": 1, "PL": 2, "GF": 3, "F_": 4}

    def fas_sort_key(filnamn):
        fn = os.path.basename(filnamn).upper()
        for prefix, prio in fas_ordning.items():
            if fn.startswith(prefix):
                return (prio, fn)
        return (9, fn)

    kombinerade = sorted(
        (os.path.join(ut_mapp, f) for f in os.listdir(ut_mapp)
         if f.lower().endswith(".pdf") and f != "MASTER_alla_kort.pdf"),
        key=fas_sort_key,
    )

    if kombinerade:
        try:
            master = PdfWriter()
            for komb_path in kombinerade:
                reader = PdfReader(komb_path)
                for page in reader.pages:
                    master.add_page(page)

            with open(master_path, "wb") as f:
                master.write(f)

            total_pages = sum(len(PdfReader(p).pages) for p in kombinerade)
            msg = f"\nMASTER: {os.path.basename(master_path)}  ({len(kombinerade)} delar, {total_pages} sidor)"
            logg.append(msg)
            print(msg)
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

    # Loggfil i samma mapp
    logg_path = os.path.join(pdf_mapp, "interfoliering_logg.txt")
    with open(logg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(logg))

    print(f"Logg: {logg_path}")


if __name__ == "__main__":
    mapp = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    interfoliera(mapp)
