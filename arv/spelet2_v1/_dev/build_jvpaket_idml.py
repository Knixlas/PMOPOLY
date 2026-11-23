# -*- coding: utf-8 -*-
"""Bygger två IDML-filer för JV-paketet:

1. JV-paket_brev_VP.idml      — 6 sidor (brev + katalog-omslag + 4 VP-sidor),
                                 DataMerge-källa: 0. Ledning/L_mottagare.csv
2. JV-paket_avatarkatalog.idml — 18 sidor, DataMerge-källa: 0. Ledning/L_personal.csv

Färger plockas från Bilder/färgschema.xlsx, typsnitt = Bahnschrift.
A4 (210×297 mm), 20 mm marginaler. Master page = sidfot + sidnummer.
"""
import csv
import os
import sys
from pathlib import Path

# Importera builder från samma mapp
sys.path.insert(0, str(Path(__file__).resolve().parent))
from idml_builder import (  # noqa: E402
    IDMLDocument, Swatch, ParagraphStyle, CharStyle, TextSpan,
    TextFrame, ImageFrame, Rectangle, Spread, MasterSpread,
    A4_W_PT, A4_H_PT, mm,
)

ROOT = Path(__file__).resolve().parent.parent
LEDNING = ROOT / "0. Ledning"
OUTPUT_DIR = LEDNING / "build_output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── Färgpalett (mappade från färgschema.xlsx) ───────────────────────
def palette() -> list[Swatch]:
    """Färger som täcker både JV-paket och övriga PMOpoly-dokument."""
    return [
        # Bas — Åke Sundvall grafisk manual
        Swatch("AS_Rod",            "EF5656"),
        Swatch("AS_Rod_Mork",       "7A2020"),
        Swatch("AS_Rodgra",         "F9F2F2"),
        Swatch("AS_Trabrun",        "DDA063"),
        Swatch("AS_Trabrun_Mork",   "7A4F20"),
        Swatch("AS_Skogsgron",      "91B542"),
        Swatch("AS_Skogsgron_Mork", "4D5E22"),
        Swatch("AS_Ljusgra",        "DDCCBF"),
        Swatch("AS_Gra",            "9E968E"),
        Swatch("AS_Gra_Mork",       "4A443E"),
        Swatch("AS_Morkgra",        "605951"),
        # Kompletterande
        Swatch("Havsbla",           "1A6B9A"),
        Swatch("Havsbla_Mork",      "0F3D5C"),
        Swatch("Massing",           "D4AF37"),
        Swatch("Massing_Mork",      "7B5020"),
        Swatch("Skiffer",           "5D737E"),
        Swatch("Skiffer_Mork",      "2F3D44"),
        # Logiska aliasar (semantiska namn för layout)
        Swatch("Text",              "231D18"),  # ink
        Swatch("Text_Muted",        "605951"),  # mörkgrå
        Swatch("Paper",             "F6EFE3"),  # bakgrund / sidor
        Swatch("Paper_Light",       "FBF6EC"),  # callout-bakgrund
        Swatch("Paper_Dark",        "ECE4D7"),  # mörkare panel
        Swatch("Line",              "CBBEAE"),  # tunn linje
        Swatch("Line_Strong",       "A89A87"),  # tjockare linje
        # Skedesfärger (från Skede-mappning)
        Swatch("Skede_PU",          "7A4F20"),  # Träbrun mörk
        Swatch("Skede_PL",          "0F3D5C"),  # Havsblå mörk
        Swatch("Skede_GF",          "4D5E22"),  # Skogsgrön mörk
        Swatch("Skede_F",           "7A2020"),  # Röd mörk
    ]


# ── Paragraph styles ─────────────────────────────────────────────────
def paragraph_styles() -> list[ParagraphStyle]:
    F = "Bahnschrift"
    return [
        # Brödtext
        ParagraphStyle("Body",         font=F, font_style="Regular",  size_pt=11, leading_pt=15, color="Text"),
        ParagraphStyle("Body Justified", font=F, font_style="Regular", size_pt=11, leading_pt=15, color="Text", align="LeftJustified"),
        ParagraphStyle("Body Small",   font=F, font_style="Regular",  size_pt=9.5, leading_pt=13, color="Text"),
        ParagraphStyle("Lead",         font=F, font_style="Light",    size_pt=15, leading_pt=22, color="Text"),
        ParagraphStyle("Salut",        font=F, font_style="Regular",  size_pt=14, leading_pt=22, color="Text"),
        # Rubriker
        ParagraphStyle("H1 Letter",    font=F, font_style="SemiBold", size_pt=30, leading_pt=35, color="Text"),
        ParagraphStyle("H1 Cover",     font=F, font_style="Bold",     size_pt=64, leading_pt=64, color="Text"),
        ParagraphStyle("H1 VP Cover",  font=F, font_style="Bold",     size_pt=88, leading_pt=82, color="Text"),
        ParagraphStyle("H1 VP",        font=F, font_style="Bold",     size_pt=44, leading_pt=48, color="Text"),
        ParagraphStyle("H1 Divider",   font=F, font_style="Bold",     size_pt=88, leading_pt=82, color="Text"),
        ParagraphStyle("H2",           font=F, font_style="Bold",     size_pt=22, leading_pt=26, color="Text"),
        ParagraphStyle("H2 Small",     font=F, font_style="Bold",     size_pt=18, leading_pt=22, color="Text"),
        ParagraphStyle("H3",           font=F, font_style="Bold",     size_pt=13, leading_pt=16, color="AS_Skogsgron_Mork", tracking=60, all_caps=True),
        # Etiketter
        ParagraphStyle("Eyebrow",      font=F, font_style="Bold",     size_pt=10, leading_pt=14, color="AS_Skogsgron_Mork", tracking=220, all_caps=True),
        ParagraphStyle("Strap",        font=F, font_style="Bold",     size_pt=11, leading_pt=14, color="Text_Muted", tracking=240, all_caps=True),
        ParagraphStyle("Page Foot",    font=F, font_style="Regular",  size_pt=9,  leading_pt=12, color="Text_Muted", tracking=160, all_caps=True),
        ParagraphStyle("Page Num",     font=F, font_style="Regular",  size_pt=10, leading_pt=12, color="Text_Muted", tracking=180),
        ParagraphStyle("Practical Label", font=F, font_style="Bold",  size_pt=9,  leading_pt=12, color="Text_Muted", tracking=200, all_caps=True),
        ParagraphStyle("Practical Value",font=F, font_style="Regular", size_pt=13, leading_pt=18, color="Text"),
        ParagraphStyle("Sig Name",     font=F, font_style="Bold",     size_pt=14, leading_pt=18, color="Text"),
        ParagraphStyle("Sig Role",     font=F, font_style="Regular",  size_pt=13, leading_pt=18, color="Text"),
        ParagraphStyle("Sig Closing",  font=F, font_style="Bold",     size_pt=9,  leading_pt=14, color="Text_Muted", tracking=180, all_caps=True),
        # Callouts
        ParagraphStyle("Callout H4",   font=F, font_style="Bold",     size_pt=9,  leading_pt=14, color="AS_Skogsgron_Mork", tracking=220, all_caps=True),
        ParagraphStyle("Callout Body", font=F, font_style="Regular",  size_pt=13, leading_pt=18, color="Text"),
        ParagraphStyle("Formula H4",   font=F, font_style="Bold",     size_pt=9,  leading_pt=14, color="Massing", tracking=220, all_caps=True),
        ParagraphStyle("Formula EQ",   font=F, font_style="Bold",     size_pt=18, leading_pt=24, color="Paper", tracking=20),
        ParagraphStyle("Formula Body", font=F, font_style="Regular",  size_pt=11, leading_pt=15, color="Paper_Dark"),
        # SWOT
        ParagraphStyle("SWOT H4 S",    font=F, font_style="Bold",     size_pt=10, leading_pt=14, color="AS_Skogsgron_Mork", tracking=220, all_caps=True),
        ParagraphStyle("SWOT H4 W",    font=F, font_style="Bold",     size_pt=10, leading_pt=14, color="AS_Rod_Mork", tracking=220, all_caps=True),
        ParagraphStyle("SWOT H4 O",    font=F, font_style="Bold",     size_pt=10, leading_pt=14, color="Havsbla_Mork", tracking=220, all_caps=True),
        ParagraphStyle("SWOT H4 T",    font=F, font_style="Bold",     size_pt=10, leading_pt=14, color="AS_Trabrun_Mork", tracking=220, all_caps=True),
        ParagraphStyle("SWOT Item",    font=F, font_style="Regular",  size_pt=11, leading_pt=15, color="Text"),
        # Skeden (på sid 23)
        ParagraphStyle("Skedet Num",   font=F, font_style="Bold",     size_pt=24, leading_pt=28, color="AS_Skogsgron_Mork"),
        ParagraphStyle("Skedet Small", font=F, font_style="Bold",     size_pt=10, leading_pt=14, color="Text_Muted", tracking=180, all_caps=True),
        # TOC
        ParagraphStyle("TOC Item",     font=F, font_style="Regular",  size_pt=14, leading_pt=22, color="Text"),
        ParagraphStyle("TOC Num",      font=F, font_style="Bold",     size_pt=11, leading_pt=22, color="AS_Skogsgron_Mork"),
        ParagraphStyle("TOC Pg",       font=F, font_style="Regular",  size_pt=10, leading_pt=22, color="Text_Muted", tracking=100),
        # Index på sid 2
        ParagraphStyle("Index H5",     font=F, font_style="Bold",     size_pt=9,  leading_pt=14, color="AS_Skogsgron_Mork", tracking=220, all_caps=True),
        ParagraphStyle("Index Item",   font=F, font_style="Regular",  size_pt=12.5, leading_pt=18, color="Text"),
        ParagraphStyle("Index Num",    font=F, font_style="Regular",  size_pt=10, leading_pt=18, color="Text_Muted", tracking=60),
        # Avatar-katalog (CV-sidor)
        ParagraphStyle("CV Name",      font=F, font_style="Bold",     size_pt=28, leading_pt=30, color="Text"),
        ParagraphStyle("CV Tagline",   font=F, font_style="Light",    size_pt=13, leading_pt=18, color="Text_Muted"),
        ParagraphStyle("CV Section",   font=F, font_style="Bold",     size_pt=10, leading_pt=14, color="AS_Skogsgron_Mork", tracking=220, all_caps=True),
        ParagraphStyle("CV Body",      font=F, font_style="Regular",  size_pt=13, leading_pt=20, color="Text"),
        ParagraphStyle("CV Pull",      font=F, font_style="Light",    size_pt=18, leading_pt=24, color="AS_Skogsgron_Mork"),
        ParagraphStyle("CV Comp Key",  font=F, font_style="Bold",     size_pt=9.5, leading_pt=14, color="Text", tracking=80),
        ParagraphStyle("CV Comp Label",font=F, font_style="Regular",  size_pt=11, leading_pt=14, color="Text"),
        ParagraphStyle("CV Project Num",font=F, font_style="Bold",    size_pt=11, leading_pt=18, color="AS_Skogsgron_Mork"),
        ParagraphStyle("CV Project Text",font=F, font_style="Regular",size_pt=12, leading_pt=18, color="Text"),
        ParagraphStyle("CV Role Tag",  font=F, font_style="Bold",     size_pt=10, leading_pt=14, color="Paper", tracking=180, all_caps=True),
        ParagraphStyle("CV Doc Id",    font=F, font_style="Regular",  size_pt=9,  leading_pt=14, color="Text_Muted", tracking=200, all_caps=True),
        ParagraphStyle("CV Initial",   font=F, font_style="Bold",     size_pt=96, leading_pt=96, color="AS_Skogsgron_Mork"),
    ]


# ── Char styles (för inline-betoningar) ─────────────────────────────
def char_styles() -> list[CharStyle]:
    return [
        CharStyle("Bold",        font_style="Bold"),
        CharStyle("SemiBold",    font_style="SemiBold"),
        CharStyle("Light",       font_style="Light"),
        CharStyle("Italic Look", font_style="Light", color="AS_Skogsgron_Mork"),
        CharStyle("Placeholder", font_style="Bold",  color="AS_Skogsgron_Mork"),  # för <<NAMN>> etc
        CharStyle("HH Color",    color="AS_Skogsgron_Mork"),
    ]


# ── Master page (sidfot + sidnummer + ramar) ────────────────────────
def build_master() -> MasterSpread:
    ms = MasterSpread(name="A-Master")
    # Bottenrad — grön accentstreck (matchar HTML:s .page::after, 6px high)
    ms.items.append(Rectangle(
        x=0, y=A4_H_PT - mm(2), w=A4_W_PT, h=mm(2),
        fill="AS_Skogsgron_Mork", stroke=None,
    ))
    return ms


# ── Bygg sidor ──────────────────────────────────────────────────────
PAGE_W = A4_W_PT
PAGE_H = A4_H_PT
MARGIN = mm(20)
CONTENT_W = PAGE_W - 2 * MARGIN
CONTENT_X = MARGIN
CONTENT_Y = MARGIN


def s(text: str, para: str = None, char: str = None, end: bool = False) -> TextSpan:
    """Bekväm konstruktor för TextSpan."""
    return TextSpan(text=text, char_style=char, para_style=para, is_paragraph_end=end)


def paragraph(para_style: str, text: str) -> list[TextSpan]:
    """Hela stycket på en gång (ingen inline-styling)."""
    return [TextSpan(text=text, para_style=para_style, is_paragraph_end=True)]


def page_footer(items: list, page_num: str, page_meta_left: str = "", page_meta_right: str = ""):
    """Lägger sidfot + sidnummer (samma layout som HTML:s .page-foot)."""
    foot_y = PAGE_H - mm(15)  # ~15mm ovanför kant
    # Vänster meta
    if page_meta_left:
        items.append(TextFrame(
            x=MARGIN, y=foot_y, w=CONTENT_W * 0.7, h=mm(8),
            spans=paragraph("Page Foot", page_meta_left),
        ))
    # Höger sidnummer
    items.append(TextFrame(
        x=PAGE_W - MARGIN - mm(40), y=foot_y, w=mm(40), h=mm(8),
        spans=paragraph("Page Num", page_num),
    ))


# ─────────── Sida 1: Anställningserbjudande (brev) ───────────
def page_letter() -> Spread:
    sp = Spread(name="01_brev")
    items = sp.items

    # Mast: HH-logotyp + namn + ref-block
    mast_y = MARGIN
    # Logotyp (placeholder-ruta)
    items.append(Rectangle(x=MARGIN, y=mast_y, w=mm(15), h=mm(15),
                           fill=None, stroke="AS_Skogsgron_Mork", stroke_weight=1.5))
    # Bolagsnamn
    items.append(TextFrame(
        x=MARGIN + mm(18), y=mast_y, w=mm(80), h=mm(15),
        spans=[s("Holiday House Holding", para="H2 Small", end=True),
               s("JOINT VENTURE-PORTFÖLJEN · ÅKEPOL", para="Page Foot", end=True)],
    ))
    # Ref-block (höger)
    items.append(TextFrame(
        x=PAGE_W - MARGIN - mm(60), y=mast_y, w=mm(60), h=mm(15),
        spans=[s("Stockholm", para="Page Num", char="Bold", end=True),
               s("<<Datum>>", para="Page Num", char="Placeholder", end=True),
               s("HHH-JV/<<Ref>>", para="Page Num", end=True)],
    ))
    # Linje under mast
    items.append(Rectangle(x=MARGIN, y=MARGIN + mm(18), w=CONTENT_W, h=0.5,
                           fill="Text", stroke=None))

    # Eyebrow + H1
    body_y = MARGIN + mm(28)
    items.append(TextFrame(
        x=MARGIN, y=body_y, w=CONTENT_W, h=mm(8),
        spans=paragraph("Eyebrow", "ANSTÄLLNINGSERBJUDANDE · OPERATIV LEDNING"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=body_y + mm(8), w=CONTENT_W, h=mm(20),
        spans=[s("<<Roll>>", para="H1 Letter", char="Placeholder"),
               s(" i ", para="H1 Letter"),
               s("<<JV_Namn>>", para="H1 Letter", char="Placeholder", end=True)],
    ))

    # Tilltalsfras
    salut_y = body_y + mm(34)
    items.append(TextFrame(
        x=MARGIN, y=salut_y, w=CONTENT_W, h=mm(8),
        spans=[s("Bästa ", para="Salut"),
               s("<<Namn>>", para="Salut", char="Placeholder"),
               s(",", para="Salut", end=True)],
    ))

    # Lead
    items.append(TextFrame(
        x=MARGIN, y=salut_y + mm(10), w=CONTENT_W, h=mm(15),
        spans=paragraph("Lead", "Det är med stor glädje vi erbjuder dig en operativ ledarroll i ett av våra joint ventures."),
    ))

    # Brödtext-block 1
    p1_y = salut_y + mm(28)
    items.append(TextFrame(
        x=MARGIN, y=p1_y, w=CONTENT_W, h=mm(28),
        spans=[
            s("Holiday House Holding AB har under det gångna året initierat tjugo joint venture-bolag tillsammans med starka operativa partners. Varje JV har ett geografiskt avgränsat uppdrag i staden Åkepol — att utveckla, bygga och förvalta ett kvarter inom en stadsdel. Du är utvald att gå in som ", para="Body Justified"),
            s("<<Roll>>", char="Placeholder"),
            s(" i ", para="Body Justified"),
            s("<<JV_Namn>>", char="Placeholder"),
            s(".", end=True),
        ],
    ))

    # H3 Bolaget
    items.append(TextFrame(
        x=MARGIN, y=p1_y + mm(32), w=CONTENT_W, h=mm(8),
        spans=paragraph("H3", "BOLAGET"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=p1_y + mm(40), w=CONTENT_W, h=mm(28),
        spans=[
            s("<<JV_Namn>>", para="Body Justified", char="Placeholder"),
            s(" är ett joint venture mellan er bolagsledning och Holiday House Holding AB. Uppdraget är avgränsat: att utveckla ett kvarter i staden Åkepol — från projektutveckling, genom planering och genomförande, till långsiktig förvaltning. Holdingbolaget står bakom som tyst men kapitalstark partner och garanterar byggnadskreditiv. Strategin lägger ni själva — det är ledningens uppgift.", end=True),
        ],
    ))

    # H3 Din ledningsgrupp
    items.append(TextFrame(
        x=MARGIN, y=p1_y + mm(72), w=CONTENT_W, h=mm(8),
        spans=paragraph("H3", "DIN LEDNINGSGRUPP"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=p1_y + mm(80), w=CONTENT_W, h=mm(20),
        spans=[
            s("Som ", para="Body Justified"),
            s("<<Roll>>", char="Placeholder"),
            s(" ingår du i en ledningsgrupp om tre personer — CEO, COO och CFO. Tillsammans utgör ni bolagsledningen och bär det operativa ansvaret från första dag. Vilka övriga medlemmar är presenteras vid uppstartspasset på konferensen.", end=True),
        ],
    ))

    # H3 Inför konferensen
    items.append(TextFrame(
        x=MARGIN, y=p1_y + mm(104), w=CONTENT_W, h=mm(8),
        spans=paragraph("H3", "INFÖR KONFERENSEN — VÄLJ DIN PROFIL"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=p1_y + mm(112), w=CONTENT_W, h=mm(36),
        spans=[
            s("Inom rollen som ", para="Body Justified"),
            s("<<Roll>>", char="Placeholder"),
            s(" kan du välja en av sex profiler som bäst representerar dig som ledare. Profilerna finns i bifogat material. Avataren har inget eget namn — det är din egen yrkeserfarenhet, kombinerad med profilens karaktär, som tas med in i ledningsgruppen. Varje profil har en specialisering, en uppsättning kompetenser och fyra relevanta projekt från karriären. Välj den profil vars styrkor du själv står för — det blir det rollen utgår från under konferensen.", end=True),
        ],
    ))

    # Practical-blocket (Datum/Plats/Tid)
    pract_y = p1_y + mm(154)
    items.append(Rectangle(
        x=MARGIN, y=pract_y, w=CONTENT_W, h=mm(20),
        fill="Paper_Light", stroke="Line", stroke_weight=0.5,
    ))
    col_w = CONTENT_W / 3
    items.append(TextFrame(
        x=MARGIN + mm(4), y=pract_y + mm(3), w=col_w - mm(4), h=mm(7),
        spans=paragraph("Practical Label", "DATUM"),
    ))
    items.append(TextFrame(
        x=MARGIN + mm(4), y=pract_y + mm(10), w=col_w - mm(4), h=mm(10),
        spans=paragraph("Practical Value", "<<Datum>>"),
    ))
    items.append(TextFrame(
        x=MARGIN + col_w + mm(2), y=pract_y + mm(3), w=col_w - mm(4), h=mm(7),
        spans=paragraph("Practical Label", "PLATS"),
    ))
    items.append(TextFrame(
        x=MARGIN + col_w + mm(2), y=pract_y + mm(10), w=col_w - mm(4), h=mm(10),
        spans=paragraph("Practical Value", "<<Plats>>"),
    ))
    items.append(TextFrame(
        x=MARGIN + 2 * col_w + mm(2), y=pract_y + mm(3), w=col_w - mm(4), h=mm(7),
        spans=paragraph("Practical Label", "TID"),
    ))
    items.append(TextFrame(
        x=MARGIN + 2 * col_w + mm(2), y=pract_y + mm(10), w=col_w - mm(4), h=mm(10),
        spans=paragraph("Practical Value", "<<Tid>>"),
    ))

    # Slutmening
    end_y = pract_y + mm(26)
    items.append(TextFrame(
        x=MARGIN, y=end_y, w=CONTENT_W, h=mm(15),
        spans=[
            s("Ingen förberedelse krävs i förväg — verksamhetsplanen för ", para="Body Justified"),
            s("<<JV_Namn>>", char="Placeholder"),
            s(" tar ni fram tillsammans i ledningsgruppen under konferensens första pass.", end=True),
        ],
    ))
    items.append(TextFrame(
        x=MARGIN, y=end_y + mm(18), w=CONTENT_W, h=mm(8),
        spans=paragraph("Body", "Vi ses!"),
    ))

    # Signatur
    sig_y = end_y + mm(32)
    items.append(Rectangle(
        x=MARGIN, y=sig_y + mm(13), w=mm(50), h=0.8,
        fill="Text", stroke=None,
    ))
    items.append(TextFrame(
        x=MARGIN + mm(54), y=sig_y, w=mm(80), h=mm(20),
        spans=[
            s("Marjorie Lindberg", para="Sig Name", end=True),
            s("Koncernchef, Holiday House Holding AB", para="Sig Role", end=True),
            s("MED VÄNLIG HÄLSNING", para="Sig Closing", end=True),
        ],
    ))

    # Sidfot
    page_footer(items, "01 / 24",
                page_meta_left="HOLIDAY HOUSE HOLDING AB · ORG. 556xxx-xxxx · SVEAVÄGEN, STOCKHOLM")
    return sp


# ─────────── Sida 2: Avatarkatalog-omslag ───────────
def page_catalogue_cover() -> Spread:
    sp = Spread(name="02_omslag")
    items = sp.items

    # Eyebrow + H1
    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(20), w=CONTENT_W, h=mm(8),
        spans=paragraph("Eyebrow", "BILAGA 1 · INFÖR KONFERENSEN"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(30), w=CONTENT_W, h=mm(40),
        spans=[
            s("Avatarkatalog", para="H1 Cover", end=True),
            s("arton profiler", para="H1 Cover", char="Italic Look", end=True),
        ],
    ))
    # Lede
    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(75), w=CONTENT_W * 0.7, h=mm(20),
        spans=paragraph("Lead", "Sex CEO-profiler, sex COO-profiler, sex CFO-profiler. Välj den karaktär vars styrkor du själv står för — det blir den ledaren du tar med dig in i ledningsgruppen."),
    ))

    # Roll-tre-grid (CEO, COO, CFO som färgade rutor)
    roles = [
        ("CEO", "Strategi, slutgiltigt mandat, riktning"),
        ("COO", "Operativt, leverans, organisation"),
        ("CFO", "Budget, kassa, balansräkning"),
    ]
    role_y = MARGIN + mm(105)
    role_w = (CONTENT_W - 2 * mm(4)) / 3
    role_h = mm(50)
    for i, (label, desc) in enumerate(roles):
        rx = MARGIN + i * (role_w + mm(4))
        items.append(Rectangle(
            x=rx, y=role_y, w=role_w, h=role_h,
            fill="Paper_Light", stroke="Line", stroke_weight=0.5,
        ))
        items.append(TextFrame(
            x=rx + mm(5), y=role_y + role_h - mm(15), w=role_w - mm(10), h=mm(7),
            spans=paragraph("Eyebrow", label),
        ))
        items.append(TextFrame(
            x=rx + mm(5), y=role_y + role_h - mm(8), w=role_w - mm(10), h=mm(8),
            spans=paragraph("Body Small", desc),
        ))

    # Index — tre kolumner med avatarnamn
    idx_y = MARGIN + mm(170)
    items.append(Rectangle(x=MARGIN, y=idx_y - 1, w=CONTENT_W, h=1, fill="Text", stroke=None))
    items.append(Rectangle(x=MARGIN, y=idx_y + mm(50), w=CONTENT_W, h=1, fill="Text", stroke=None))
    col_w = CONTENT_W / 3
    cols = [
        ("CEO · 6 PROFILER", [("Skepparen","03"),("Förhandlaren","04"),("Värden","05"),("Profilen","06"),("Klippan","07"),("Medlaren","08")]),
        ("COO · 6 PROFILER", [("Urmakaren","09"),("Förmannen","10"),("Generalen","11"),("Pionjären","12"),("Bron","13"),("Brandsläckaren","14")]),
        ("CFO · 6 PROFILER", [("Rödpennan","15"),("Strategen","16"),("Vakthunden","17"),("Statistikern","18"),("Berättaren","19"),("Skattmästaren","20")]),
    ]
    for c, (heading, rows) in enumerate(cols):
        cx = MARGIN + c * col_w
        items.append(TextFrame(
            x=cx + mm(3), y=idx_y + mm(2), w=col_w - mm(6), h=mm(7),
            spans=paragraph("Index H5", heading),
        ))
        spans = []
        for name, pg in rows:
            spans.append(s(f"{name}    {pg}", para="Index Item", end=True))
        items.append(TextFrame(
            x=cx + mm(3), y=idx_y + mm(10), w=col_w - mm(6), h=mm(38),
            spans=spans,
        ))

    # Hur du läser/väljer
    bot_y = idx_y + mm(58)
    items.append(TextFrame(
        x=MARGIN, y=bot_y, w=CONTENT_W * 0.48, h=mm(8),
        spans=paragraph("Practical Label", "HUR DU LÄSER KORTET"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=bot_y + mm(8), w=CONTENT_W * 0.48, h=mm(28),
        spans=paragraph("Body Small", "Karaktärsbeskrivning, kompetensprofil (STA / KOM / SAM / NOG / INN / ABM, 0–2 prickar) och fyra projekt från karriären — en kondenserad meritförteckning."),
    ))
    items.append(TextFrame(
        x=MARGIN + CONTENT_W * 0.52, y=bot_y, w=CONTENT_W * 0.48, h=mm(8),
        spans=paragraph("Practical Label", "HUR DU VÄLJER"),
    ))
    items.append(TextFrame(
        x=MARGIN + CONTENT_W * 0.52, y=bot_y + mm(8), w=CONTENT_W * 0.48, h=mm(28),
        spans=paragraph("Body Small", "Läs alla sex profiler för din roll. Pricka in den profil vars styrkor matchar din egen yrkeserfarenhet bäst. Bekräftas vid uppstartspasset."),
    ))

    page_footer(items, "02 / 24", page_meta_left="HHH-JV · AVATARKATALOG · BILAGA 1")
    return sp


# ─────────── Sida 21: Verksamhetsplan omslag ───────────
def page_vp_cover() -> Spread:
    sp = Spread(name="21_vp_omslag")
    items = sp.items

    # Mast
    mast_y = MARGIN
    items.append(Rectangle(x=MARGIN, y=mast_y, w=mm(13), h=mm(13),
                           fill=None, stroke="AS_Skogsgron_Mork", stroke_weight=1.5))
    items.append(TextFrame(
        x=MARGIN + mm(16), y=mast_y, w=mm(80), h=mm(13),
        spans=[s("Holiday House Holding", para="H2 Small", end=True),
               s("JOINT VENTURE-PORTFÖLJEN", para="Page Foot", end=True)],
    ))
    items.append(TextFrame(
        x=PAGE_W - MARGIN - mm(60), y=mast_y, w=mm(60), h=mm(13),
        spans=[s("Bilaga 2", para="Page Num", char="Bold", end=True),
               s("VP/<<JV_Namn>>", para="Page Num", char="Placeholder", end=True),
               s("SPELOMGÅNG 2026", para="Page Num", end=True)],
    ))

    # Strap + H1 + Deck
    title_y = MARGIN + mm(60)
    items.append(TextFrame(
        x=MARGIN, y=title_y, w=CONTENT_W, h=mm(8),
        spans=paragraph("Strap", "VERKSAMHETSPLAN · ÅKEPOL"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=title_y + mm(10), w=CONTENT_W, h=mm(80),
        spans=[s("Byggt med", para="H1 VP Cover", end=True),
               s("tärning", para="H1 VP Cover", char="Italic Look", end=True)],
    ))
    items.append(TextFrame(
        x=MARGIN, y=title_y + mm(95), w=CONTENT_W, h=mm(28),
        spans=paragraph("Lead", "Ett joint venture i staden Åkepol — från projektutveckling, genom planering och genomförande, till långsiktig förvaltning."),
    ))

    # Doc-meta nederst (2x2 grid)
    meta_y = MARGIN + mm(220)
    items.append(Rectangle(x=MARGIN, y=meta_y - mm(2), w=CONTENT_W, h=1.5, fill="Text", stroke=None))
    meta_items = [
        ("BOLAG", "<<JV_Namn>>"),
        ("LEDNING", "<<Roll>>"),
        ("SPELOMGÅNG", "2026"),
        ("DOKUMENTSTATUS", "Uppdateras inte under spelets gång"),
    ]
    for i, (label, val) in enumerate(meta_items):
        col, row = i % 2, i // 2
        mx = MARGIN + col * (CONTENT_W / 2)
        my = meta_y + mm(4) + row * mm(15)
        items.append(TextFrame(
            x=mx, y=my, w=CONTENT_W / 2 - mm(6), h=mm(6),
            spans=paragraph("Practical Label", label),
        ))
        items.append(TextFrame(
            x=mx, y=my + mm(6), w=CONTENT_W / 2 - mm(6), h=mm(8),
            spans=paragraph("Practical Value", val),
        ))

    page_footer(items, "21 / 24", page_meta_left="VERKSAMHETSPLAN · ÅKEPOL · STRATEGISK KOMPASS")
    return sp


# ─────────── Sida 22: VP Uppdrag och vision ───────────
def page_vp_uppdrag() -> Spread:
    sp = Spread(name="22_vp_uppdrag")
    items = sp.items

    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(8), w=CONTENT_W, h=mm(8),
        spans=paragraph("Eyebrow", "KAPITEL 1 · BAKGRUND OCH UPPDRAG"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(18), w=CONTENT_W, h=mm(40),
        spans=paragraph("H1 VP", "Bygg det förvaltningsbolag som vinner spelet."),
    ))
    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(58), w=CONTENT_W, h=mm(28),
        spans=paragraph("Lead", "Bolaget verkar inom svensk fastighetsutveckling — en bransch som kombinerar långsiktigt kapital, kortsiktiga politiska beslut och tekniska realiteter. Marken är ändlig, byggrätterna är politiska, kostnaderna är reala och energikraven skärps år för år."),
    ))

    # Vision + Affärsidé (två kolumner)
    col_y = MARGIN + mm(92)
    col_w = (CONTENT_W - mm(8)) / 2
    items.append(TextFrame(
        x=MARGIN, y=col_y, w=col_w, h=mm(8),
        spans=paragraph("H3", "VISION"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=col_y + mm(8), w=col_w, h=mm(35),
        spans=paragraph("Body", "Att skapa stadens mest omtyckta områden — kvarter med vackra, funktionella och hållbara hus där människor och verksamheter växer och trivs långt efter att vi byggt klart."),
    ))
    items.append(TextFrame(
        x=MARGIN + col_w + mm(8), y=col_y, w=col_w, h=mm(8),
        spans=paragraph("H3", "AFFÄRSIDÉ"),
    ))
    items.append(TextFrame(
        x=MARGIN + col_w + mm(8), y=col_y + mm(8), w=col_w, h=mm(35),
        spans=paragraph("Body", "Att utveckla, bygga och förvalta hus på det mest kostnadseffektiva och hållbara sättet. Vi tar projekt från idé till färdig drift, med rätt kompetenser i varje skede."),
    ))

    # Callout 1: Joint venture
    co1_y = MARGIN + mm(140)
    items.append(Rectangle(
        x=MARGIN, y=co1_y, w=CONTENT_W, h=mm(28),
        fill="Paper_Light", stroke=None,
    ))
    items.append(Rectangle(
        x=MARGIN, y=co1_y, w=mm(1.5), h=mm(28),
        fill="AS_Skogsgron_Mork", stroke=None,
    ))
    items.append(TextFrame(
        x=MARGIN + mm(5), y=co1_y + mm(3), w=CONTENT_W - mm(8), h=mm(6),
        spans=paragraph("Callout H4", "JOINT VENTURE MED MODERBOLAGET"),
    ))
    items.append(TextFrame(
        x=MARGIN + mm(5), y=co1_y + mm(9), w=CONTENT_W - mm(8), h=mm(18),
        spans=paragraph("Callout Body", "Moderbolaget är en tyst men ekonomiskt stark partner. Driver inget operativt, men garanterar byggnadskreditivet under produktionen och kan skjuta in moderbolagslån om kapitalet inte räcker — 100 Mkr nominellt per lån, 95 Mkr betalas ut, hela 100 dras vid slutvärderingen. Sista utvägen, inte en strategi."),
    ))

    # Callout 2: Slutformeln (mörk bakgrund, gold accent)
    co2_y = co1_y + mm(34)
    items.append(Rectangle(
        x=MARGIN, y=co2_y, w=CONTENT_W, h=mm(38),
        fill="AS_Gra_Mork", stroke=None,
    ))
    items.append(Rectangle(
        x=MARGIN, y=co2_y, w=mm(1.5), h=mm(38),
        fill="Massing", stroke=None,
    ))
    items.append(TextFrame(
        x=MARGIN + mm(5), y=co2_y + mm(3), w=CONTENT_W - mm(8), h=mm(6),
        spans=paragraph("Formula H4", "SLUTFORMELN"),
    ))
    items.append(TextFrame(
        x=MARGIN + mm(5), y=co2_y + mm(9), w=CONTENT_W - mm(8), h=mm(10),
        spans=paragraph("Formula EQ", "Poäng = (FV × 30 % × Energibonus + EK + TB) ÷ (BTA / 1000)"),
    ))
    items.append(TextFrame(
        x=MARGIN + mm(5), y=co2_y + mm(20), w=CONTENT_W - mm(8), h=mm(16),
        spans=paragraph("Formula Body", "FV = fastighetsvärde · EK = eget kapital · TB = täckningsbidrag · BTA = bruttototalarea. Det finns ingen halvvinst. Den med högst poäng vinner."),
    ))

    # Devis
    dev_y = co2_y + mm(46)
    items.append(TextFrame(
        x=MARGIN, y=dev_y, w=CONTENT_W, h=mm(8),
        spans=[s("ER DEVIS: ", para="H3"),
               s("BYGGT MED TÄRNING", para="H3", char="Italic Look", end=True)],
    ))
    items.append(TextFrame(
        x=MARGIN, y=dev_y + mm(10), w=CONTENT_W, h=mm(20),
        spans=paragraph("Body", "Verkligheten följer inte alltid planen. Det handlar inte om att eliminera slumpen, utan om att fatta så bra beslut att slumpen blir hanterbar. När ni står vid ett vägval ska den här verksamhetsplanen ge er riktning. Den uppdateras inte — när den är skriven är den skriven."),
    ))

    page_footer(items, "22 / 24", page_meta_left="VERKSAMHETSPLAN · KAPITEL 1")
    return sp


# ─────────── Sida 23: SWOT + tre skeden ───────────
def page_vp_swot() -> Spread:
    sp = Spread(name="23_vp_swot")
    items = sp.items

    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(8), w=CONTENT_W, h=mm(8),
        spans=paragraph("Eyebrow", "KAPITEL 4 · MARKNAD OCH STRATEGI"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(18), w=CONTENT_W, h=mm(20),
        spans=paragraph("H1 VP", "SWOT — så ser läget ut."),
    ))

    # SWOT 2x2
    swot_y = MARGIN + mm(48)
    quad_w = (CONTENT_W - mm(4)) / 2
    quad_h = mm(50)
    quads = [
        ("STYRKOR", "SWOT H4 S", [
            "Hela värdekedjan internt, från idé till förvaltning",
            "Tärningar i alla format (D4 till D20)",
            "Tillgång till moderbolagslån vid behov",
            "80 företagskulturkort att köpa kompetens från",
            "Möjlighet att samla riskbuffertar redan i Skede 1",
        ]),
        ("SVAGHETER", "SWOT H4 W", [
            "Begränsad startkassa, ABT-budgeten räcker bara om ni inte slösar",
            "Tärningarna är opartiska och ofta otacksamma",
            "Moderbolagslån kostar 5 Mkr i avgift",
            "Företagskulturkort har en pristrappa som stiger",
            "Sämre energiklass straffas hårt i Förvaltningen",
        ]),
        ("MÖJLIGHETER", "SWOT H4 O", [
            "Återbruk, lågkolbetong och hög energiklass premieras",
            "Långsiktiga hyresgäster ger stabila kassaflöden",
            "Stark efterfrågan på bostäder med god energiklass",
            "Statliga renoveringsbidrag och positiv mediebild",
            "Smart yield-tajming kan hävja ett medioker projekt",
        ]),
        ("HOT", "SWOT H4 T", [
            "Räntechock, pandemins eftereffekter, demografisk förskjutning",
            "Vakanser, prischock på byggmaterial, fettavskiljarbråk",
            "E-handel, hyrestak, oannonserade tillsynsbesök",
            "Asbest, radon, andra dolda fynd vid förvärv",
            "Att forcera slutskedet ger dyra garantianmärkningar",
        ]),
    ]
    for i, (heading, h_style, lst) in enumerate(quads):
        col, row = i % 2, i // 2
        qx = MARGIN + col * (quad_w + mm(4))
        qy = swot_y + row * (quad_h + mm(4))
        items.append(Rectangle(x=qx, y=qy, w=quad_w, h=quad_h,
                               fill="Paper_Light", stroke="Line", stroke_weight=0.5))
        items.append(TextFrame(
            x=qx + mm(4), y=qy + mm(3), w=quad_w - mm(8), h=mm(6),
            spans=paragraph(h_style, heading),
        ))
        spans = [s("• " + t, para="SWOT Item", end=True) for t in lst]
        items.append(TextFrame(
            x=qx + mm(4), y=qy + mm(10), w=quad_w - mm(8), h=quad_h - mm(13),
            spans=spans,
        ))

    # H2 + tre skeden
    sk_y = swot_y + 2 * (quad_h + mm(4)) + mm(4)
    items.append(TextFrame(
        x=MARGIN, y=sk_y, w=CONTENT_W, h=mm(12),
        spans=paragraph("H2", "Verksamheten i tre skeden"),
    ))
    skeden = [
        ("1", "PROJEKTUTVECKLING", "Markförvärv, projektval, nämndbeslut",
         "Projektchefen driver ett programhandlingsarbete för att maximera kvarterets potential. 4×4 mark + eventuella expansioner, godkända projekt, fastställda Q- och H-krav, beräknad ABT-budget."),
        ("2", "PLANERING · GENOMFÖRANDE", "Upphandling, organisation, åtta utförandefaser",
         "Arbetschefen tar över. 13 planeringssteg, leverantörer i nivå 1–4, organisation och händelsekort. Sedan åtta FAS-kort där kompetens spelas mot utfallsnivå — slumpen styr händelser, ert kunnande styr ekonomin."),
        ("3", "FÖRVALTNING", "Fyra kvartal med drift, händelser, energi",
         "Fastighetschefen leder den löpande driften. Yieldförändringar, omvärldskort, händelsekort per fastighet, beslut om köp/sälj och energiuppgraderingar. Det är här slutpoängen materialiseras."),
    ]
    sk_h = mm(20)
    for i, (num, pill, h, body) in enumerate(skeden):
        sy = sk_y + mm(15) + i * sk_h
        items.append(Rectangle(x=MARGIN, y=sy, w=CONTENT_W, h=0.5, fill="Line", stroke=None))
        items.append(TextFrame(
            x=MARGIN, y=sy + mm(3), w=mm(12), h=mm(15),
            spans=paragraph("Skedet Num", num),
        ))
        items.append(TextFrame(
            x=MARGIN + mm(15), y=sy + mm(3), w=CONTENT_W - mm(15), h=mm(5),
            spans=paragraph("Skedet Small", pill),
        ))
        items.append(TextFrame(
            x=MARGIN + mm(15), y=sy + mm(8), w=CONTENT_W - mm(15), h=mm(5),
            spans=paragraph("H2 Small", h),
        ))
        items.append(TextFrame(
            x=MARGIN + mm(15), y=sy + mm(13), w=CONTENT_W - mm(15), h=mm(8),
            spans=paragraph("Body Small", body),
        ))

    page_footer(items, "23 / 24", page_meta_left="VERKSAMHETSPLAN · KAPITEL 4–6")
    return sp


# ─────────── Sida 24: Strategiska val ───────────
def page_vp_strategi() -> Spread:
    sp = Spread(name="24_vp_strategi")
    items = sp.items

    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(8), w=CONTENT_W, h=mm(8),
        spans=paragraph("Eyebrow", "KAPITEL 7 · STRATEGISKA VAL OCH ARBETSSÄTT"),
    ))
    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(18), w=CONTENT_W, h=mm(20),
        spans=paragraph("H1 VP", "När det blåser — luta er hit."),
    ))
    items.append(TextFrame(
        x=MARGIN, y=MARGIN + mm(42), w=CONTENT_W, h=mm(15),
        spans=paragraph("Lead", "Värderingarna håller, taktiken justeras. Här är de fokusområden ni ska luta er mot när marknaden ändras kortsiktigt."),
    ))

    # Fyra fokusområden i 2x2 grid
    foc_y = MARGIN + mm(70)
    col_w = (CONTENT_W - mm(8)) / 2
    h_each = mm(28)
    focuses = [
        ("HÅLLBARHET", "Inte bara strategi — ett mätetal. Energiklass A ger värdebonus +20 %, B +15 %, C +10 %, D +5 %, E är referens (0 %). Uppgradering kostar 3 Mkr per steg. Räkna på det."),
        ("RISK OCH RISKBUFFERT", "Riskbuffertar är er försäkring mot tärningens nyckfullhet. En oanvänd Rb är värd noll vid slutet. Använd dem."),
        ("EKONOMI", "Anskaffningen ska räcka till tomtkostnad, markexpansion och utveckling. Det som blir kvar är er ABT-budget. Glöm inte att moderbolaget förväntar sig ett täckningsbidrag — gör inte slut på pengarna bara för att de finns där."),
        ("SUND KONKURRENS", "Ni främjar en spelomgång fri från korruption, fusk och utrop. Det är inte fel att vinna; det är fel att vinna på fel sätt. Ni ska kunna förklara era val utan att vrida på sanningen."),
    ]
    for i, (h, body) in enumerate(focuses):
        col, row = i % 2, i // 2
        fx = MARGIN + col * (col_w + mm(8))
        fy = foc_y + row * (h_each + mm(4))
        items.append(TextFrame(
            x=fx, y=fy, w=col_w, h=mm(6),
            spans=paragraph("H3", h),
        ))
        items.append(TextFrame(
            x=fx, y=fy + mm(7), w=col_w, h=h_each - mm(7),
            spans=paragraph("Body Small", body),
        ))

    # Callout: Kunder, medbyggare, ambassadörer
    co_y = foc_y + 2 * (h_each + mm(4)) + mm(8)
    items.append(Rectangle(
        x=MARGIN, y=co_y, w=CONTENT_W, h=mm(28),
        fill="Paper_Light", stroke=None,
    ))
    items.append(Rectangle(
        x=MARGIN, y=co_y, w=mm(1.5), h=mm(28),
        fill="AS_Skogsgron_Mork", stroke=None,
    ))
    items.append(TextFrame(
        x=MARGIN + mm(5), y=co_y + mm(3), w=CONTENT_W - mm(8), h=mm(6),
        spans=paragraph("Callout H4", "KUNDER, MEDBYGGARE, AMBASSADÖRER"),
    ))
    items.append(TextFrame(
        x=MARGIN + mm(5), y=co_y + mm(9), w=CONTENT_W - mm(8), h=mm(18),
        spans=[
            s("Kunder: ", para="Callout Body", char="Bold"),
            s("bostadsköpare, hyresgäster, beställare. ", para="Callout Body"),
            s("Möjliggörare: ", char="Bold"),
            s("Stadsbyggnadskontoret, Stadshuset, Länsstyrelsen, Skönhetsrådet. "),
            s("Medbyggare: ", char="Bold"),
            s("leverantörer och organisation från Skede 2.1. "),
            s("Ambassadörer: ", char="Bold"),
            s("FC och FS som tar hand om fastigheterna i Skede 3.", end=True),
        ],
    ))

    # Dokumentstruktur (TOC)
    toc_y = co_y + mm(36)
    items.append(TextFrame(
        x=MARGIN, y=toc_y, w=CONTENT_W, h=mm(10),
        spans=paragraph("H2 Small", "Dokumentstrukturen i Åkepol"),
    ))
    toc_items = [
        ("01", "Verksamhetsplanen", "er strategiska kompass. Läses först.", "DETTA"),
        ("02", "Projektledningsplanen", "internt arbete genom Skede 2.1 Planering.", "SEPARAT"),
        ("03", "Projektplanen", "externt avtal med medbyggarna i Skede 2.2 Genomförande.", "SEPARAT"),
        ("04", "Förvaltningsplanen", "drift, hyresgäster och affär i Skede 3 Förvaltning.", "SEPARAT"),
        ("05", "Regelhäftet", "det praktiska spelet, hur ni utför momenten.", "SEPARAT"),
    ]
    for i, (num, name, sub, pg) in enumerate(toc_items):
        ty = toc_y + mm(12) + i * mm(8)
        items.append(Rectangle(x=MARGIN, y=ty + mm(7), w=CONTENT_W, h=0.3, fill="Line", stroke=None))
        items.append(TextFrame(
            x=MARGIN, y=ty, w=mm(10), h=mm(6),
            spans=paragraph("TOC Num", num),
        ))
        items.append(TextFrame(
            x=MARGIN + mm(12), y=ty, w=CONTENT_W - mm(30), h=mm(6),
            spans=[s(name, para="TOC Item", char="Bold"),
                   s(" — " + sub, para="TOC Item", end=True)],
        ))
        items.append(TextFrame(
            x=MARGIN + CONTENT_W - mm(18), y=ty, w=mm(18), h=mm(6),
            spans=paragraph("TOC Pg", pg),
        ))

    page_footer(items, "24 / 24", page_meta_left="VERKSAMHETSPLAN · KAPITEL 7")
    return sp


# ─────────── Bygger brev_VP IDML ───────────
def build_brev_vp():
    doc = IDMLDocument()
    doc.swatches = palette()
    doc.paragraph_styles = paragraph_styles()
    doc.char_styles = char_styles()
    doc.master_spreads = [build_master()]
    doc.spreads = [
        page_letter(),
        page_catalogue_cover(),
        page_vp_cover(),
        page_vp_uppdrag(),
        page_vp_swot(),
        page_vp_strategi(),
    ]
    out = OUTPUT_DIR / "JV-paket_brev_VP.idml"
    doc.write(str(out))
    print(f"Skrev {out}")
    print(f"  Sidor: {len(doc.spreads)}, paragraph styles: {len(doc.paragraph_styles)}, swatches: {len(doc.swatches)}")
    return out


# ─────────── Bygger avatarkatalog IDML (sidor 3-20) ───────────
def load_avatars():
    """Läser L_personal.csv och returnerar lista över avatarer (18 st)."""
    path = LEDNING / "L_personal.csv"
    rows = []
    with open(path, encoding="cp1252") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            if r.get("Roll") and r.get("Namn"):  # filtrera tomma rader
                rows.append(r)
    return rows


def page_avatar_cv(avatar: dict, page_num: int, total_for_role: int) -> Spread:
    """En CV-sida för en avatar. Vänsterspalt: porträtt + namn + kompetenser.
    Högerspalt: roll-meta + karaktär + pull quote + fyra projekt.
    """
    sp = Spread(name=f"{page_num:02d}_{avatar['Roll']}_{avatar['Namn']}")
    items = sp.items

    role = avatar["Roll"]
    name = avatar["Namn"]
    tagline = avatar.get("Specialisering", "")
    desc = avatar.get("Beskrivning", "")
    img_path = avatar.get("@bild", "")
    role_idx = int(avatar["ID"].split("-")[1]) if "-" in avatar["ID"] else 1

    # Vänsterspalt — bakgrund
    left_x = MARGIN
    left_y = MARGIN
    left_w = mm(70)
    left_h = PAGE_H - 2 * MARGIN
    items.append(Rectangle(
        x=left_x, y=left_y, w=left_w, h=left_h,
        fill="Paper_Light", stroke="Line", stroke_weight=0.5,
    ))

    # Porträtt (image frame om sökvägen finns)
    port_x = left_x + mm(5)
    port_y = left_y + mm(5)
    port_w = left_w - mm(10)
    port_h = port_w  # kvadratisk
    if img_path and os.path.exists(img_path):
        items.append(ImageFrame(
            x=port_x, y=port_y, w=port_w, h=port_h,
            image_path=img_path,
            stroke="Line_Strong", stroke_weight=0.5,
        ))
    else:
        # Fallback — initial-ruta
        items.append(Rectangle(
            x=port_x, y=port_y, w=port_w, h=port_h,
            fill="Paper_Dark", stroke="Line_Strong", stroke_weight=0.5,
        ))
        items.append(TextFrame(
            x=port_x, y=port_y + port_h * 0.3, w=port_w, h=port_h * 0.5,
            spans=paragraph("CV Initial", name[:1]),
        ))
    # Roll-tagg ovanför porträttet
    items.append(Rectangle(
        x=port_x + mm(2), y=port_y + mm(2), w=mm(14), h=mm(6),
        fill="AS_Skogsgron_Mork", stroke=None,
    ))
    items.append(TextFrame(
        x=port_x + mm(2), y=port_y + mm(3), w=mm(14), h=mm(5),
        spans=paragraph("CV Role Tag", role),
    ))

    # Namn + tagline
    name_y = port_y + port_h + mm(4)
    items.append(TextFrame(
        x=port_x, y=name_y, w=port_w, h=mm(15),
        spans=paragraph("CV Name", name),
    ))
    items.append(TextFrame(
        x=port_x, y=name_y + mm(15), w=port_w, h=mm(12),
        spans=paragraph("CV Tagline", tagline),
    ))

    # Linje
    items.append(Rectangle(x=port_x, y=name_y + mm(28), w=port_w, h=0.3, fill="Line", stroke=None))

    # Kompetensprofil
    comp_y = name_y + mm(32)
    items.append(TextFrame(
        x=port_x, y=comp_y, w=port_w, h=mm(6),
        spans=paragraph("CV Section", "KOMPETENSPROFIL"),
    ))
    keys = [("STA", "Stabilitet"), ("KOM", "Kommunikation"), ("SAM", "Samarbete"),
            ("NOG", "Noggrannhet"), ("INN", "Innovation"), ("ABM", "Arbetsmiljö")]
    for i, (k, label) in enumerate(keys):
        cy = comp_y + mm(8) + i * mm(7)
        v = avatar.get(k, "-")
        try:
            n = int(v) if v not in ("-", "") else 0
        except ValueError:
            n = 0
        items.append(TextFrame(
            x=port_x, y=cy, w=mm(10), h=mm(5),
            spans=paragraph("CV Comp Key", k),
        ))
        items.append(TextFrame(
            x=port_x + mm(11), y=cy, w=port_w - mm(28), h=mm(5),
            spans=paragraph("CV Comp Label", label),
        ))
        # Två prickar (fylld om n >= position)
        for d in range(2):
            dx = port_x + port_w - mm(11) + d * mm(4)
            dy = cy + mm(1)
            items.append(Rectangle(
                x=dx, y=dy, w=mm(2.5), h=mm(2.5),
                fill="AS_Skogsgron_Mork" if d < n else None,
                stroke="AS_Skogsgron_Mork", stroke_weight=0.4,
            ))

    # Linje
    items.append(Rectangle(x=port_x, y=comp_y + mm(56), w=port_w, h=0.3, fill="Line", stroke=None))

    # Mekanik-fotnot
    mek_y = left_y + left_h - mm(20)
    items.append(TextFrame(
        x=port_x, y=mek_y, w=port_w, h=mm(5),
        spans=paragraph("CV Section", "SPELMEKANIK"),
    ))
    items.append(TextFrame(
        x=port_x, y=mek_y + mm(6), w=port_w, h=mm(12),
        spans=paragraph("Body Small", "Företagskultur — används i Genomförandefasen. Kastas när det används."),
    ))

    # Högerspalt
    right_x = left_x + left_w + mm(8)
    right_w = CONTENT_W - left_w - mm(8)
    right_y = MARGIN

    # Top-meta
    items.append(TextFrame(
        x=right_x, y=right_y, w=right_w * 0.7, h=mm(6),
        spans=paragraph("CV Section", f"{role} · PROFIL {role_idx:02d} AV 06"),
    ))
    role_desc = {"CEO": "Övergripande ansvar och slutgiltigt beslutsmandat",
                 "COO": "Ansvarar för det operativa och för verkställandet",
                 "CFO": "Ansvarar för budget, kassaflöde och ekonomisk uppföljning"}.get(role, "")
    items.append(TextFrame(
        x=right_x, y=right_y + mm(7), w=right_w * 0.7, h=mm(5),
        spans=paragraph("CV Tagline", role_desc),
    ))
    items.append(TextFrame(
        x=right_x + right_w * 0.7, y=right_y, w=right_w * 0.3, h=mm(5),
        spans=paragraph("CV Doc Id", f"HHH/CV/{role}-{role_idx:02d}"),
    ))
    items.append(Rectangle(x=right_x, y=right_y + mm(14), w=right_w, h=0.5, fill="Text", stroke=None))

    # Karaktär
    char_y = right_y + mm(20)
    items.append(TextFrame(
        x=right_x, y=char_y, w=right_w, h=mm(5),
        spans=paragraph("CV Section", "KARAKTÄR"),
    ))
    items.append(TextFrame(
        x=right_x, y=char_y + mm(7), w=right_w, h=mm(48),
        spans=paragraph("CV Body", desc),
    ))

    # Pull quote (första meningen)
    pull_y = char_y + mm(60)
    pull = desc.split(".")[0] + "." if "." in desc else desc[:120]
    items.append(Rectangle(
        x=right_x, y=pull_y, w=mm(1.5), h=mm(20),
        fill="AS_Skogsgron_Mork", stroke=None,
    ))
    items.append(TextFrame(
        x=right_x + mm(4), y=pull_y, w=right_w - mm(4), h=mm(20),
        spans=paragraph("CV Pull", f"“{pull}”"),
    ))

    # Fyra projekt
    proj_y = pull_y + mm(28)
    items.append(TextFrame(
        x=right_x, y=proj_y, w=right_w, h=mm(5),
        spans=paragraph("CV Section", "FYRA PROJEKT FRÅN KARRIÄREN"),
    ))
    items.append(Rectangle(x=right_x, y=proj_y + mm(7), w=right_w, h=0.3, fill="Line", stroke=None))
    proj_h = mm(15)
    for i in range(4):
        py = proj_y + mm(8) + i * proj_h
        text = avatar.get(f"Projekt{i+1}", "")
        items.append(TextFrame(
            x=right_x, y=py + mm(2), w=mm(8), h=mm(5),
            spans=paragraph("CV Project Num", f"{i+1:02d}"),
        ))
        items.append(TextFrame(
            x=right_x + mm(10), y=py, w=right_w - mm(10), h=proj_h,
            spans=paragraph("CV Project Text", text),
        ))
        items.append(Rectangle(x=right_x, y=py + proj_h, w=right_w, h=0.3, fill="Line", stroke=None))

    # Footer note
    foot_note_y = right_y + left_h - mm(30)
    items.append(Rectangle(x=right_x, y=foot_note_y, w=right_w, h=0.5, fill="Line", stroke=None))
    items.append(TextFrame(
        x=right_x, y=foot_note_y + mm(2), w=right_w, h=mm(5),
        spans=paragraph("CV Doc Id", f"FÖRETAGSKULTUR · {role} · PROFILVAL BEKRÄFTAS VID UPPSTARTSPASSET"),
    ))

    # Sidfot
    page_footer(items, f"{page_num:02d} / 24",
                page_meta_left=f"HHH-JV · AVATARKATALOG · {role.upper()} — {name.upper()}")
    return sp


def build_avatarkatalog():
    """Bygger 18 CV-sidor (en per avatar) som ETT IDML-dokument.
    När DataMerge anropas på det här dokumentet behövs egentligen ingen merge —
    sidorna är redan unika med inbäddat innehåll.
    """
    doc = IDMLDocument()
    doc.swatches = palette()
    doc.paragraph_styles = paragraph_styles()
    doc.char_styles = char_styles()
    doc.master_spreads = [build_master()]

    avatars = load_avatars()
    if len(avatars) != 18:
        print(f"Varning: förväntade 18 avatarer, fick {len(avatars)}")
    # Sortera per roll: CEO 1-6, COO 1-6, CFO 1-6 (sidor 3-8, 9-14, 15-20)
    role_order = {"CEO": 0, "COO": 1, "CFO": 2}
    avatars.sort(key=lambda a: (role_order.get(a["Roll"], 9),
                                int(a["ID"].split("-")[1])))

    page_num = 3
    for av in avatars:
        sp = page_avatar_cv(av, page_num, total_for_role=6)
        doc.spreads.append(sp)
        page_num += 1

    out = OUTPUT_DIR / "JV-paket_avatarkatalog.idml"
    doc.write(str(out))
    print(f"Skrev {out}")
    print(f"  Sidor: {len(doc.spreads)}, paragraph styles: {len(doc.paragraph_styles)}, swatches: {len(doc.swatches)}")
    return out


def main():
    build_brev_vp()
    build_avatarkatalog()


if __name__ == "__main__":
    main()

