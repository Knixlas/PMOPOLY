# -*- coding: utf-8 -*-
"""Minimal test-IDML: 1 sida, 1 textframe, "Hello"."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from idml_builder import (  # noqa: E402
    IDMLDocument, ParagraphStyle, TextSpan, TextFrame, Spread, MasterSpread, mm
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "0. Ledning" / "build_output" / "TEST_minimal.idml"

doc = IDMLDocument()
doc.paragraph_styles = [ParagraphStyle("Body", size_pt=14, leading_pt=18)]
doc.master_spreads = [MasterSpread(name="A-Master")]

sp = Spread(name="01_test")
sp.items.append(TextFrame(
    x=mm(20), y=mm(30), w=mm(170), h=mm(20),
    spans=[TextSpan(text="Hello från IDML-byggaren — om du ser det här fungerar grunden.",
                    para_style="Body", is_paragraph_end=True)],
))
doc.spreads = [sp]
doc.write(str(OUT))
print(f"Skrev {OUT}")

