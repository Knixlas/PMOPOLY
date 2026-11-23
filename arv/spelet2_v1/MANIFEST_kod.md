# MANIFEST – kod från SPELET 2 (version 1 Åkepol)

Källa: Dropbox `/SPELET 2 - version 1 Åkepol/` (fryst kopia 2026-05-13). Arkiverad 2026-09-26 via Dropbox-fetch (textextraktion), orörd.

Undantaget enligt uppdrag: `Mentorsprogram/`, `.claude/`, `Old/versionsdubletter_2026-05/`, `__pycache__`.

Om storlekar: fetch returnerar text med en extra avslutande radbrytning, så de flesta arkiverade filer är exakt 1 byte större än i Dropbox. Radslut är normaliserade till LF (fetch levererar `\n`); ev. CRLF i original (t.ex. .bat) syns inte. Avvikelser utöver +1 byte anges i status.

| Relativ sökväg | Storlek i Dropbox (byte) | Status |
|---|---:|---|
| `AUTOMATISERING.md` | 6614 | arkiverad |
| `ANALYS_RAPPORT.md` | 10563 | arkiverad |
| `CLAUDE.md` | 9135 | arkiverad |
| `REGELBOK_CHECKLIST.md` | 10861 | arkiverad |
| `JV-paket.html` | 39751 | ej arkiverad – fetch returnerar endast extraherad brödtext (HTML-taggar/CSS borttagna, ~8 kB av 39,8 kB); originalet kan inte hämtas orört med tillgängliga verktyg |
| `excel_till_config.bat` | 596 | arkiverad |
| `interfoliera.bat` | 593 | arkiverad |
| `konvertera_former.bat` | 582 | arkiverad |
| `excel_till_config.py` | 7802 | arkiverad |
| `förbered_csv.py` | 3072 | arkiverad |
| `interfoliera_pdf.py` | 8590 | arkiverad |
| `konvertera_former_till_png.py` | 5871 | arkiverad |
| `provkort_ark.py` | 11553 | arkiverad |
| `skapa_tryckark.py` | 22250 | arkiverad |
| `master_kortproduktion.jsx` | 29656 | arkiverad |
| `master_test.jsx` | 3431 | arkiverad |
| `master_tryckbart.jsx` | 15385 | arkiverad |
| `0. Ledning/skapa mail.bat` | 593 | arkiverad |
| `0. Ledning/skapa_utkast.ps1` | 9984 | arkiverad (−2 byte: trolig UTF-8-BOM borttagen av fetch) |
| `0. Ledning/planer/applicera_omslag.py` | 5134 | arkiverad (−44 byte mot Dropbox; ingen avslutande extra radbrytning – troligen radslut/blanktecken normaliserade av fetch, innehållet i övrigt komplett) |
| `0. Ledning/planer/docx_to_markdown.py` | 14097 | arkiverad |
| `0. Ledning/planer/markdown_to_pdf.py` | 11778 | arkiverad |
| `0. Ledning/planer/splitta_planer.py` | 6037 | arkiverad |
| `1. Projektutveckling/generate_forms_v2.py` | 7841 | arkiverad |
| `1. Projektutveckling/generate_svg.py` | 8134 | arkiverad |
| `Bilder/big_bang_skriv_om_prompter.py` | 46259 | arkiverad |
| `Bilder/generate_images_v6.py` | 35565 | arkiverad |
| `Bilder/patch_excel_testprompter.py` | 13821 | arkiverad |
| `Bilder/shape_mask.py` | 2836 | arkiverad |
| `Bilder/uppdatera_färger.py` | 22197 | arkiverad |
| `Mallar Indesign/diagnos_ejFC.jsx` | 4307 | arkiverad |
| `Mallar Indesign/diagnos_exemplar.jsx` | 2869 | arkiverad |
| `Mallar Indesign/diagnostik_en_fil.jsx` | 2581 | arkiverad |
| `Mallar Indesign/diagnostik_platshallare.jsx` | 4159 | arkiverad |
| `Mallar Indesign/farglagg_projektkort.jsx` | 50757 | arkiverad |
| `Mallar Indesign/farglagg_projektkort_v27_fast.jsx` | 50948 | arkiverad |
| `Mallar Indesign/lagg_till_fargkodramar.jsx` | 1473 | arkiverad |
| `Mallar Indesign/lagg_till_fargkodramar_alla.jsx` | 2647 | arkiverad |
| `Mallar Indesign/master_kortproduktion.jsx` | 29656 | arkiverad (identisk med rotens master_kortproduktion.jsx – samma storlek, innehåll kontrollerat vid fetch; kopierad) |
| `Mallar Indesign/master_test.jsx` | 3431 | arkiverad (identisk med rotens master_test.jsx – samma storlek/tidsstämpel, innehåll kontrollerat; kopierad) |
| `Mallar Indesign/master_tryckbart.jsx` | 19161 | arkiverad |
| `Mallar Indesign/splitta_tryckeri.py` | 22573 | arkiverad |
| `Mallar Indesign/synka_skript_till_indesign.bat` | 1182 | arkiverad |
| `Mallar Indesign/tryckeri_58x88.jsx` | 544 | arkiverad |
| `Mallar Indesign/tryckeri_88x146.jsx` | 548 | arkiverad |
| `Mallar Indesign/tryckeri_88x88.jsx` | 544 | arkiverad |
| `Mallar Indesign/tryckeri_engine.jsx` | 36063 | arkiverad |
| `Mallar Indesign/typsnitt_block.jsx` | 3769 | arkiverad |
| `Old/kategori5_2026-05/analys_abt.py` | 12165 | arkiverad |
| `Old/kategori5_2026-05/husbyggspelet.py` | 183408 | arkiverad |
| `Old/kategori5_2026-05/simulering.py` | 13291 | arkiverad |
| `Old/kategori5_2026-05/spelare_aggressiv.py` | 6184 | arkiverad |
| `Old/kategori5_2026-05/spelare_forsiktig.py` | 6216 | arkiverad |
| `Old/kategori5_2026-05/spelare_kassabyggare.py` | 5123 | arkiverad |
| `Old/kategori5_2026-05/spelare_kvalitet.py` | 5847 | arkiverad |
| `Old/kategori5_2026-05/spelare_optimal.py` | 32496 | arkiverad |
| `_dev/build_jvpaket_idml.py` | 51275 | arkiverad |
| `_dev/build_minimal_test.py` | 882 | arkiverad |
| `_dev/generate_mottagardata.py` | 3885 | arkiverad |
| `_dev/idml_builder.py` | 27458 | arkiverad |
