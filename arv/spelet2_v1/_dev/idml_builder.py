# -*- coding: utf-8 -*-
"""Minimal IDML-byggare för PMOpoly-dokument.

Genererar IDML (Adobe InDesign Markup Language) — en ZIP med XML-filer
som InDesign kan öppna och spara om som .indd. Stödet är inte komplett
mot IDML-specen utan optimerat för: A4 enkel-sidor, paragraph styles
(Bahnschrift), swatches från färgschema, master pages med sidfot/sidnummer,
text frames med inbäddat story-innehåll, image frames med länkad PNG,
DataMerge-platshållare som löpande text.
"""
import os
import zipfile
from dataclasses import dataclass, field
from typing import Optional
from xml.sax.saxutils import escape


# ── Storheter ────────────────────────────────────────────────────────
PT_PER_MM = 72.0 / 25.4
A4_W_MM, A4_H_MM = 210.0, 297.0
A4_W_PT = A4_W_MM * PT_PER_MM   # 595.276 pt
A4_H_PT = A4_H_MM * PT_PER_MM   # 841.890 pt


def mm(v: float) -> float:
    return v * PT_PER_MM


# ── Datamodell ───────────────────────────────────────────────────────
@dataclass
class Swatch:
    name: str
    hex: str  # "RRGGBB" utan #

    def cmyk_or_rgb_attr(self) -> str:
        r = int(self.hex[0:2], 16)
        g = int(self.hex[2:4], 16)
        b = int(self.hex[4:6], 16)
        return f"{r} {g} {b}"


@dataclass
class ParagraphStyle:
    name: str
    font: str = "Bahnschrift"
    font_style: str = "Regular"   # InDesign font style name
    size_pt: float = 11.0
    leading_pt: float = 14.0
    color: str = "Text"           # swatch name
    tracking: int = 0             # 1/1000 em (InDesign Tracking)
    align: str = "LeftAlign"      # LeftAlign, CenterAlign, RightAlign, LeftJustified, FullyJustified
    space_before: float = 0.0
    space_after: float = 0.0
    all_caps: bool = False


@dataclass
class CharStyle:
    name: str
    font: Optional[str] = None
    font_style: Optional[str] = None
    color: Optional[str] = None
    size_pt: Optional[float] = None


@dataclass
class TextSpan:
    text: str
    char_style: Optional[str] = None  # CharStyle name
    para_style: Optional[str] = None  # ParagraphStyle (only for first span in paragraph)
    is_paragraph_end: bool = False    # om True läggs <Br/> efter


@dataclass
class TextFrame:
    x: float       # vänster (pt) från sidans top-left
    y: float       # topp (pt)
    w: float       # bredd (pt)
    h: float       # höjd (pt)
    spans: list    # list[TextSpan] — en eller flera stycken
    fill: Optional[str] = None       # swatch name eller None
    stroke: Optional[str] = None     # swatch name eller None
    stroke_weight: float = 0.0
    inset_top: float = 0.0
    inset_right: float = 0.0
    inset_bottom: float = 0.0
    inset_left: float = 0.0


@dataclass
class ImageFrame:
    x: float
    y: float
    w: float
    h: float
    image_path: str  # absolut sökväg
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_weight: float = 0.0


@dataclass
class Rectangle:
    x: float
    y: float
    w: float
    h: float
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_weight: float = 0.0


@dataclass
class Spread:
    name: str
    items: list = field(default_factory=list)    # TextFrame | ImageFrame | Rectangle
    master: Optional[str] = "A-Master"


@dataclass
class MasterSpread:
    name: str       # t.ex. "A-Master"
    items: list = field(default_factory=list)


# ── IDML-genering ────────────────────────────────────────────────────
class IDMLDocument:
    def __init__(self, page_w_pt: float = A4_W_PT, page_h_pt: float = A4_H_PT):
        self.page_w = page_w_pt
        self.page_h = page_h_pt
        self.swatches: list[Swatch] = []
        self.paragraph_styles: list[ParagraphStyle] = []
        self.char_styles: list[CharStyle] = []
        self.fonts: set[str] = set()
        self.master_spreads: list[MasterSpread] = []
        self.spreads: list[Spread] = []
        self._uid_counter = 1000

    def next_uid(self, prefix: str = "u") -> str:
        self._uid_counter += 1
        return f"{prefix}{self._uid_counter}"

    # Skapar IDML på disk. path är full sökväg incl .idml-suffix.
    def write(self, path: str):
        # Samla unika fonter från paragraph styles
        for ps in self.paragraph_styles:
            self.fonts.add(ps.font)
        for cs in self.char_styles:
            if cs.font:
                self.fonts.add(cs.font)

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            # mimetype måste vara först och okomprimerad
            zi = zipfile.ZipInfo("mimetype")
            zi.compress_type = zipfile.ZIP_STORED
            z.writestr(zi, "application/vnd.adobe.indesign-idml-package")

            z.writestr("META-INF/container.xml", _container_xml())
            z.writestr("Resources/Fonts.xml", self._fonts_xml())
            z.writestr("Resources/Graphic.xml", self._graphic_xml())
            z.writestr("Resources/Styles.xml", self._styles_xml())
            z.writestr("Resources/Preferences.xml", self._preferences_xml())

            master_paths = []
            for ms in self.master_spreads:
                p = f"MasterSpreads/MasterSpread_{ms.name}.xml"
                z.writestr(p, self._master_spread_xml(ms))
                master_paths.append(p)

            spread_paths = []
            stories: dict[str, str] = {}  # story_self -> xml
            for sp in self.spreads:
                p = f"Spreads/Spread_{sp.name}.xml"
                xml, story_xml_map = self._spread_xml(sp)
                z.writestr(p, xml)
                spread_paths.append(p)
                stories.update(story_xml_map)

            story_paths = []
            for s_self, s_xml in stories.items():
                p = f"Stories/Story_{s_self}.xml"
                z.writestr(p, s_xml)
                story_paths.append(p)

            z.writestr(
                "designmap.xml",
                self._designmap_xml(master_paths, spread_paths, story_paths),
            )

    # ── XML-genererare ──────────────────────────────────────────────
    def _fonts_xml(self) -> str:
        # Minimal font-deklaration: bara FontFamily + Font-stubbar utan
        # PostScript-namn eller FontType. Då matchar InDesign mot installerad
        # font via Name + FontStyleName istället för hårdkodade PS-namn.
        font_xml = []
        for fname in sorted(self.fonts):
            family_self = f"FontFamily/{fname}"
            styles = ["Regular", "Bold", "Light", "SemiBold", "SemiLight",
                      "Light Condensed", "SemiBold Condensed", "Bold Condensed"]
            font_entries = []
            for st in styles:
                style_id = st.replace(" ", "")
                font_entries.append(
                    f'\t\t<Font Self="{family_self}/$ID/{style_id}" '
                    f'FontFamily="{fname}" '
                    f'Name="{fname} {st}" '
                    f'FontStyleName="{st}" '
                    f'Status="Installed"/>'
                )
            font_xml.append(
                f'\t<FontFamily Self="{family_self}" Name="{fname}">\n'
                + "\n".join(font_entries)
                + '\n\t</FontFamily>'
            )
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?aid style="50" type="snippet" readerVersion="6.0" featureSet="513" product="9.0(370)" ?>
<idPkg:Fonts xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="9.0">
{chr(10).join(font_xml)}
</idPkg:Fonts>
"""

    def _graphic_xml(self) -> str:
        # Standard-färger som InDesign vill ha
        std = [
            '<Color Self="Color/Black" Model="Process" Space="CMYK" ColorValue="0 0 0 100" Name="Black" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937" AlternateSpace="NoAlternateColor" AlternateColorValue=""/>',
            '<Color Self="Color/Paper" Model="Process" Space="CMYK" ColorValue="0 0 0 0" Name="Paper" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937" AlternateSpace="NoAlternateColor" AlternateColorValue=""/>',
            '<Color Self="Color/Registration" Model="Registration" Space="CMYK" ColorValue="100 100 100 100" Name="Registration" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937" AlternateSpace="NoAlternateColor" AlternateColorValue=""/>',
            '<Color Self="Color/u3a" Model="Process" Space="RGB" ColorValue="0 0 0" Name="None" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937" AlternateSpace="NoAlternateColor" AlternateColorValue=""/>',
        ]
        custom = []
        for sw in self.swatches:
            custom.append(
                f'<Color Self="Color/{_xml_id(sw.name)}" Model="Process" Space="RGB" '
                f'ColorValue="{sw.cmyk_or_rgb_attr()}" Name="{escape(sw.name)}" '
                'ColorEditable="true" ColorRemovable="true" Visible="true" '
                'SwatchCreatorID="7937" AlternateSpace="NoAlternateColor" AlternateColorValue=""/>'
            )
        # None-swatch + standard line/fill swatches behövs
        std_swatches = [
            '<Swatch Self="Swatch/None" Name="None" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937"/>',
        ]
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?aid style="50" type="snippet" readerVersion="6.0" featureSet="513" product="9.0(370)" ?>
<idPkg:Graphic xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="9.0">
{chr(10).join(std)}
{chr(10).join(custom)}
{chr(10).join(std_swatches)}
<StrokeStyle Self="StrokeStyle/$ID/Solid" Name="$ID/Solid"/>
<StrokeStyle Self="StrokeStyle/$ID/ThinThin" Name="$ID/ThinThin"/>
</idPkg:Graphic>
"""

    def _styles_xml(self) -> str:
        # Bygg paragraph styles
        para_xml = []
        # ROOT/DEFAULT-stil krävs av InDesign
        para_xml.append(
            '<RootParagraphStyleGroup Self="u_RootParagraphStyleGroup">\n'
            '<ParagraphStyle Self="ParagraphStyle/$ID/[No paragraph style]" '
            'Name="$ID/[No paragraph style]" '
            'AppliedFont="Bahnschrift" FontStyle="Regular" PointSize="11" Leading="14" '
            'Tracking="0" Justification="LeftAlign"/>'
        )
        for ps in self.paragraph_styles:
            justification = ps.align
            attrs = (
                f'Self="ParagraphStyle/{_xml_id(ps.name)}" '
                f'Name="{escape(ps.name)}" '
                f'AppliedFont="{ps.font}" '
                f'FontStyle="{ps.font_style}" '
                f'PointSize="{ps.size_pt}" '
                f'Leading="{ps.leading_pt}" '
                f'Tracking="{ps.tracking}" '
                f'Justification="{justification}" '
                f'FillColor="Color/{_xml_id(ps.color)}" '
                f'SpaceBefore="{ps.space_before}" '
                f'SpaceAfter="{ps.space_after}" '
                f'Capitalization="{"AllCaps" if ps.all_caps else "Normal"}" '
                f'NextStyle="ParagraphStyle/$ID/[No paragraph style]" '
                f'BasedOn="ParagraphStyle/$ID/[No paragraph style]"'
            )
            para_xml.append(f'<ParagraphStyle {attrs}/>')
        para_xml.append('</RootParagraphStyleGroup>')

        # Char styles
        char_xml = ['<RootCharacterStyleGroup Self="u_RootCharacterStyleGroup">',
                    '<CharacterStyle Self="CharacterStyle/$ID/[No character style]" '
                    'Name="$ID/[No character style]"/>']
        for cs in self.char_styles:
            attrs = [f'Self="CharacterStyle/{_xml_id(cs.name)}"', f'Name="{escape(cs.name)}"',
                     'BasedOn="CharacterStyle/$ID/[No character style]"']
            if cs.font:
                attrs.append(f'AppliedFont="{cs.font}"')
            if cs.font_style:
                attrs.append(f'FontStyle="{cs.font_style}"')
            if cs.size_pt:
                attrs.append(f'PointSize="{cs.size_pt}"')
            if cs.color:
                attrs.append(f'FillColor="Color/{_xml_id(cs.color)}"')
            char_xml.append(f'<CharacterStyle {" ".join(attrs)}/>')
        char_xml.append('</RootCharacterStyleGroup>')

        # Cell/Table/Object/TOC styles — minimum stub
        stubs = [
            '<RootCellStyleGroup Self="u_RootCellStyleGroup"><CellStyle Self="CellStyle/$ID/[None]" Name="$ID/[None]"/></RootCellStyleGroup>',
            '<RootTableStyleGroup Self="u_RootTableStyleGroup"><TableStyle Self="TableStyle/$ID/[No table style]" Name="$ID/[No table style]"/></RootTableStyleGroup>',
            '<RootObjectStyleGroup Self="u_RootObjectStyleGroup"><ObjectStyle Self="ObjectStyle/$ID/[None]" Name="$ID/[None]"/><ObjectStyle Self="ObjectStyle/$ID/[Normal Graphics Frame]" Name="$ID/[Normal Graphics Frame]"/><ObjectStyle Self="ObjectStyle/$ID/[Normal Text Frame]" Name="$ID/[Normal Text Frame]"/><ObjectStyle Self="ObjectStyle/$ID/[Normal Grid]" Name="$ID/[Normal Grid]"/></RootObjectStyleGroup>',
            '<RootTOCStyleGroup Self="u_RootTOCStyleGroup"/>',
        ]

        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?aid style="50" type="snippet" readerVersion="6.0" featureSet="513" product="9.0(370)" ?>
<idPkg:Styles xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="9.0">
{chr(10).join(para_xml)}
{chr(10).join(char_xml)}
{chr(10).join(stubs)}
</idPkg:Styles>
"""

    def _preferences_xml(self) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?aid style="50" type="snippet" readerVersion="6.0" featureSet="513" product="9.0(370)" ?>
<idPkg:Preferences xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="9.0">
<DocumentPreference Self="dDocPref" PageHeight="{self.page_h}" PageWidth="{self.page_w}" PageOrientation="Portrait" PagesPerDocument="1" FacingPages="false"/>
<MarginPreference Self="dMarginPref" Top="{mm(20)}" Bottom="{mm(20)}" Left="{mm(20)}" Right="{mm(20)}" ColumnCount="1" ColumnGutter="12"/>
<TransparencyPreference Self="dTransparencyPref"/>
<ViewPreference Self="dViewPref" HorizontalMeasurementUnits="Millimeters" VerticalMeasurementUnits="Millimeters"/>
</idPkg:Preferences>
"""

    def _master_spread_xml(self, ms: MasterSpread) -> str:
        items_xml, stories_xml = [], {}
        for it in ms.items:
            x, sx = self._render_item(it, base_x=0, base_y=0)
            items_xml.append(x)
            stories_xml.update(sx)
        # ms.name antas vara t.ex. "A-Master" — split på första "-"
        prefix, _, base = ms.name.partition("-")
        if not base:
            base = ms.name
            prefix = "A"
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?aid style="50" type="snippet" readerVersion="6.0" featureSet="513" product="9.0(370)" ?>
<idPkg:MasterSpread xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="9.0">
<MasterSpread Self="MasterSpread_{ms.name}" Name="{escape(ms.name)}" NamePrefix="{prefix}" BaseName="{escape(base)}" ShowMasterItems="true" PageCount="1">
<Page Self="MasterPage_{ms.name}_1" Name="{prefix}" AppliedTrapPreset="TrapPreset/$ID/kDefaultTrapStyleName" GeometricBounds="0 0 {self.page_h} {self.page_w}" ItemTransform="1 0 0 1 0 0" MasterPageTransform="1 0 0 1 0 0">
<MarginPreference ColumnCount="1" ColumnGutter="12" Top="{mm(20)}" Bottom="{mm(20)}" Left="{mm(20)}" Right="{mm(20)}"/>
</Page>
{chr(10).join(items_xml)}
</MasterSpread>
</idPkg:MasterSpread>
"""

    def _spread_xml(self, sp: Spread) -> tuple[str, dict[str, str]]:
        items_xml, stories = [], {}
        for it in sp.items:
            x, sx = self._render_item(it, base_x=0, base_y=0)
            items_xml.append(x)
            stories.update(sx)
        applied_master = f"MasterSpread_{sp.master}" if sp.master else "n"
        return (f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?aid style="50" type="snippet" readerVersion="6.0" featureSet="513" product="9.0(370)" ?>
<idPkg:Spread xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="9.0">
<Spread Self="Spread_{sp.name}" PageCount="1" BindingLocation="0" AllowPageShuffle="true" ItemTransform="1 0 0 1 0 0" ShowMasterItems="true" PageTransitionType="None">
<Page Self="Page_{sp.name}_1" GeometricBounds="0 0 {self.page_h} {self.page_w}" ItemTransform="1 0 0 1 0 0" Name="{sp.name}" AppliedMaster="{applied_master}" OverrideList="" TabOrder="" GridStartingPoint="TopOutside">
<MarginPreference ColumnCount="1" ColumnGutter="12" Top="{mm(20)}" Bottom="{mm(20)}" Left="{mm(20)}" Right="{mm(20)}"/>
</Page>
{chr(10).join(items_xml)}
</Spread>
</idPkg:Spread>
""", stories)

    def _render_item(self, it, base_x: float, base_y: float) -> tuple[str, dict[str, str]]:
        if isinstance(it, TextFrame):
            return self._render_text_frame(it, base_x, base_y)
        if isinstance(it, ImageFrame):
            return self._render_image_frame(it, base_x, base_y), {}
        if isinstance(it, Rectangle):
            return self._render_rectangle(it, base_x, base_y), {}
        return "", {}

    def _frame_geometric_bounds(self, item, base_x, base_y) -> str:
        # IDML: GeometricBounds = "y1 x1 y2 x2"
        x1 = item.x + base_x
        y1 = item.y + base_y
        x2 = x1 + item.w
        y2 = y1 + item.h
        return f"{y1} {x1} {y2} {x2}"

    def _fill_stroke_attrs(self, item) -> str:
        fill = f'Color/{_xml_id(item.fill)}' if item.fill else 'Swatch/None'
        stroke = f'Color/{_xml_id(item.stroke)}' if item.stroke else 'Swatch/None'
        return (f' FillColor="{fill}" StrokeColor="{stroke}" '
                f'StrokeWeight="{item.stroke_weight}"')

    def _render_text_frame(self, tf: TextFrame, bx: float, by: float) -> tuple[str, dict[str, str]]:
        story_self = self.next_uid("story")
        story_xml = self._story_xml(story_self, tf.spans)
        gb = self._frame_geometric_bounds(tf, bx, by)
        frame_self = self.next_uid("tf")
        attrs = self._fill_stroke_attrs(tf)
        text_frame_xml = f"""<TextFrame Self="{frame_self}" ParentStory="{story_self}" PreviousTextFrame="n" NextTextFrame="n" ContentType="TextType" GeometricBounds="{gb}" ItemLayer="ub" ItemTransform="1 0 0 1 0 0"{attrs}>
<Properties><PathGeometry><GeometryPathType PathOpen="false">
<PathPointArray>
<PathPointType Anchor="{tf.x+bx} {tf.y+by}" LeftDirection="{tf.x+bx} {tf.y+by}" RightDirection="{tf.x+bx} {tf.y+by}"/>
<PathPointType Anchor="{tf.x+bx} {tf.y+tf.h+by}" LeftDirection="{tf.x+bx} {tf.y+tf.h+by}" RightDirection="{tf.x+bx} {tf.y+tf.h+by}"/>
<PathPointType Anchor="{tf.x+tf.w+bx} {tf.y+tf.h+by}" LeftDirection="{tf.x+tf.w+bx} {tf.y+tf.h+by}" RightDirection="{tf.x+tf.w+bx} {tf.y+tf.h+by}"/>
<PathPointType Anchor="{tf.x+tf.w+bx} {tf.y+by}" LeftDirection="{tf.x+tf.w+bx} {tf.y+by}" RightDirection="{tf.x+tf.w+bx} {tf.y+by}"/>
</PathPointArray>
</GeometryPathType></PathGeometry></Properties>
<TextFramePreference TextColumnCount="1" TextColumnGutter="12" Inset="{tf.inset_top} {tf.inset_left} {tf.inset_bottom} {tf.inset_right}"/>
</TextFrame>"""
        return text_frame_xml, {story_self: story_xml}

    def _story_xml(self, story_self: str, spans: list) -> str:
        body = []
        # Stycken: gruppera spans tills is_paragraph_end=True (eller sista span)
        para = []
        for s in spans:
            para.append(s)
            if s.is_paragraph_end or s is spans[-1]:
                body.append(self._para_xml(para))
                para = []
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?aid style="50" type="snippet" readerVersion="6.0" featureSet="513" product="9.0(370)" ?>
<idPkg:Story xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="9.0">
<Story Self="{story_self}" AppliedTOCStyle="n" TrackChanges="false" StoryTitle="$ID/" AppliedNamedGrid="n">
{chr(10).join(body)}
</Story>
</idPkg:Story>
"""

    def _para_xml(self, spans: list) -> str:
        if not spans:
            return ""
        applied_para = "ParagraphStyle/$ID/[No paragraph style]"
        for s in spans:
            if s.para_style:
                applied_para = f"ParagraphStyle/{_xml_id(s.para_style)}"
                break
        char_runs = []
        for s in spans:
            applied_char = f"CharacterStyle/{_xml_id(s.char_style)}" if s.char_style else "CharacterStyle/$ID/[No character style]"
            text = s.text.replace("\r", "").replace("\n", "")
            # InDesign vill ha <Br/> mellan stycken; vi bygger en CharacterStyleRange per span
            char_runs.append(
                f'<CharacterStyleRange AppliedCharacterStyle="{applied_char}">'
                f'<Content>{escape(text)}</Content>'
                f'</CharacterStyleRange>'
            )
        # Lägg en avslutande Br om sista span markerar styckeavslut
        end_br = '<Br/>' if spans[-1].is_paragraph_end else ''
        return f'<ParagraphStyleRange AppliedParagraphStyle="{applied_para}">{"".join(char_runs)}{end_br}</ParagraphStyleRange>'

    def _render_image_frame(self, im: ImageFrame, bx: float, by: float) -> str:
        gb = self._frame_geometric_bounds(im, bx, by)
        frame_self = self.next_uid("if")
        link_self = self.next_uid("link")
        attrs = self._fill_stroke_attrs(im)
        # Windows: C:\... → file:///C:/...
        href = im.image_path.replace("\\", "/")
        if not href.startswith("/"):
            href = "/" + href
        href = "file://" + href
        ext = im.image_path.rsplit(".", 1)[-1].upper() if "." in im.image_path else "PNG"
        fmt_map = {"PNG": "$ID/Portable Network Graphics (PNG)",
                   "JPG": "$ID/JPEG", "JPEG": "$ID/JPEG",
                   "PSD": "$ID/Photoshop", "TIF": "$ID/TIFF", "TIFF": "$ID/TIFF"}
        fmt = fmt_map.get(ext, "$ID/Portable Network Graphics (PNG)")
        return f"""<Rectangle Self="{frame_self}" ContentType="GraphicType" GeometricBounds="{gb}" ItemLayer="ub" ItemTransform="1 0 0 1 0 0"{attrs}>
<Properties><PathGeometry><GeometryPathType PathOpen="false">
<PathPointArray>
<PathPointType Anchor="{im.x+bx} {im.y+by}" LeftDirection="{im.x+bx} {im.y+by}" RightDirection="{im.x+bx} {im.y+by}"/>
<PathPointType Anchor="{im.x+bx} {im.y+im.h+by}" LeftDirection="{im.x+bx} {im.y+im.h+by}" RightDirection="{im.x+bx} {im.y+im.h+by}"/>
<PathPointType Anchor="{im.x+im.w+bx} {im.y+im.h+by}" LeftDirection="{im.x+im.w+bx} {im.y+im.h+by}" RightDirection="{im.x+im.w+bx} {im.y+im.h+by}"/>
<PathPointType Anchor="{im.x+im.w+bx} {im.y+by}" LeftDirection="{im.x+im.w+bx} {im.y+by}" RightDirection="{im.x+im.w+bx} {im.y+by}"/>
</PathPointArray>
</GeometryPathType></PathGeometry></Properties>
<Image Self="{frame_self}_image" ItemTransform="1 0 0 1 0 0" ImageTypeName="{fmt}">
<Link Self="{link_self}" LinkResourceURI="{escape(href)}" LinkResourceFormat="{fmt}" StoredState="Normal" LinkClassID="35906" LinkClientID="257" LinkResourceModified="false" LinkObjectModified="false" ShowInUI="true" CanEmbed="true" CanUnembed="true" CanPackage="true" ImportPolicy="NoAutoImport" ExportPolicy="NoAutoExport" LinkImportStamp="$ID/" LinkImportModificationTime="$ID/" LinkImportTime="$ID/" LinkResourceSize="0~0"/>
</Image>
</Rectangle>"""

    def _render_rectangle(self, r: Rectangle, bx: float, by: float) -> str:
        gb = self._frame_geometric_bounds(r, bx, by)
        frame_self = self.next_uid("rect")
        attrs = self._fill_stroke_attrs(r)
        return f"""<Rectangle Self="{frame_self}" ContentType="Unassigned" GeometricBounds="{gb}" ItemLayer="ub" ItemTransform="1 0 0 1 0 0"{attrs}>
<Properties><PathGeometry><GeometryPathType PathOpen="false">
<PathPointArray>
<PathPointType Anchor="{r.x+bx} {r.y+by}" LeftDirection="{r.x+bx} {r.y+by}" RightDirection="{r.x+bx} {r.y+by}"/>
<PathPointType Anchor="{r.x+bx} {r.y+r.h+by}" LeftDirection="{r.x+bx} {r.y+r.h+by}" RightDirection="{r.x+bx} {r.y+r.h+by}"/>
<PathPointType Anchor="{r.x+r.w+bx} {r.y+r.h+by}" LeftDirection="{r.x+r.w+bx} {r.y+r.h+by}" RightDirection="{r.x+r.w+bx} {r.y+r.h+by}"/>
<PathPointType Anchor="{r.x+r.w+bx} {r.y+by}" LeftDirection="{r.x+r.w+bx} {r.y+by}" RightDirection="{r.x+r.w+bx} {r.y+by}"/>
</PathPointArray>
</GeometryPathType></PathGeometry></Properties>
</Rectangle>"""

    def _designmap_xml(self, master_paths, spread_paths, story_paths) -> str:
        spread_links = "\n\t".join(
            f'<idPkg:Spread src="{p}"/>' for p in spread_paths
        )
        master_links = "\n\t".join(
            f'<idPkg:MasterSpread src="{p}"/>' for p in master_paths
        )
        story_links = "\n\t".join(
            f'<idPkg:Story src="{p}"/>' for p in story_paths
        )
        # Story-list (alla self-IDs som whitespace-separerad lista)
        story_list = " ".join(p.replace("Stories/Story_", "").replace(".xml", "")
                              for p in story_paths)
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?aid style="50" type="document" readerVersion="6.0" featureSet="513" product="9.0(370)" ?>
<Document xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="9.0" Self="dDoc" Name="$ID/" NoteMode="ToolTip" StoryList="{story_list}" ActiveLayer="ub" UnusedSwatches="" PreflightProfile="" ZeroPoint="0 0" AccurateLPIandAngle="false" CMYKProfile="$ID/" RGBProfile="$ID/" SolidColorIntent="UseColorSettings" AfterBlendingIntent="UseColorSettings" DefaultImageIntent="UseColorSettings" RGBPolicy="UseEmbeddedProfile" CMYKPolicy="UseEmbeddedProfile">
\t<Language Self="Language/$ID/sv_SE" Name="$ID/sv_SE" SingleQuotes="‘’" DoubleQuotes="“”" PrimaryLanguageName="$ID/Swedish" SublanguageName="$ID/Sweden" Id="1053"/>
\t<idPkg:Graphic src="Resources/Graphic.xml"/>
\t<idPkg:Fonts src="Resources/Fonts.xml"/>
\t<idPkg:Styles src="Resources/Styles.xml"/>
\t<idPkg:Preferences src="Resources/Preferences.xml"/>
\t<Layer Self="ub" Name="Layer 1" Visible="true" Locked="false" IgnoreWrap="false" ShowGuides="true" LockGuides="false" UI="true" Expendable="true" Printable="true" LayerColor="LightBlue" Merged="false"/>
\t{master_links}
\t{spread_links}
\t{story_links}
</Document>
"""


# ── Hjälpare ─────────────────────────────────────────────────────────
_BAD_CHARS = ' /\\?*:"<>|.()[]{},;\'`@#%^&+=!~'

def _xml_id(name: str) -> str:
    """Konvertera ett namn till en IDML-säker id (utan mellanslag/specialtecken)."""
    out = []
    for c in name:
        if c.isalnum() or c == "_" or c == "-":
            out.append(c)
        else:
            out.append("_")
    s = "".join(out)
    return s if s else "X"


def _container_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
\t<rootfiles>
\t\t<rootfile full-path="designmap.xml" media-type="application/vnd.adobe.indesign-idml-package"/>
\t</rootfiles>
</container>
"""

