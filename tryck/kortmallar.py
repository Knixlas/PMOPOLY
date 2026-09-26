"""Kortmallar i HTML: en funktion per kortsida. Innehållet kommer ur kortdata/*.xlsx.

Samma mallar används för tryckfilerna (tryck/bygg_tryck.py) och kan användas av onlinespelet.
Mått i millimeter; färger enligt de tryckta korten (Produktion-fliken i Excel).
"""
import html
from pathlib import Path

ROT = Path(__file__).resolve().parent
BILDER = ROT / "bilder"

# Förvaltningens röda palett (som de tryckta F-korten)
F = {"rod": "#EF5656", "mork": "#7A2020", "rosa": "#FDE6E6", "kram": "#FCF6EF", "text": "#2B2323"}
# Projektkortens färger per typ: (mörk, ljus) från PU_projekt.xlsx / Produktion
TYPFARG = {"BRF": ("#7a3835", "#f6e2dd"), "FÖRSKOLA": ("#3f4a1f", "#e9ebd5"), "LOKAL": ("#6e4a18", "#f1e3c6"),
           "KONTOR": ("#363f4a", "#e0e5ea"), "HYRESRÄTT": ("#6b5a2c", "#f1ead2")}
TYPBILD = {"HYRESRÄTT": "Hyresrätt Generell", "FÖRSKOLA": "FÖRSKOLOR Generell", "LOKAL": "LOKAL Generell",
           "KONTOR": "KONTOR Generell"}

# Skedenas färger (skede_color i Produktion-fliken): markerar i vilken del av spelet uppgiften används
SKEDE = {"PU": "#DDA063", "PL": "#1A6B9A", "G": "#91B542", "F": "#EF5656"}
# Kubfärgerna på scoreboarden (bekräftat av Niklas): visar vilken kub kravet flyttar
KUB = {"H": "#4E9A3A", "Q": "#7B4FA0", "T": "#E08A2E"}
BILDPREFIX = {"FÖRSKOLA": "FÖRSKOLOR", "KONTOR": "KONTOR", "LOKAL": "LOKAL", "HYRESRÄTT": "Hyresrätt", "BRF": "BRF"}
# FC och FS: befintliga personalbilder (Bilder/Skapade bilder)
PERSONBILD = {"Förhandlaren": "Fastighetschef Kommersiellt", "Tekniska experten": "Fastighetschef Samhälle",
              "Skölden": "Fastighetschef Kommersiellt_2", "Bostadsveteranen": "Fastighetschef Bostäder",
              "Nätverkaren": "Fastighetschef Generalist", "Den lugna": "Fastighetstekniker Generalist_2",
              "FS-1": "Fastighetstekniker Teknisk", "FS-2": "Fastighetstekniker Bostäder", "FS-3": "Fastighetstekniker Generalist",
              "FS-4": "Fastighetstekniker Bostäder_2", "FS-5": "Fastighetstekniker Kommersiellt", "FS-6": "Fastighetstekniker Samhälle"}

REGEL = {   # händelse- och kvartalskortens effekter i spelarens ord
    "dolt_plus_dn": "Lägg en <b>dold plusbricka</b> på fastigheten.",
    "dolt_minus_dn": "Lägg en <b>dold minusbricka</b> på fastigheten.",
    "energi_plus": "Lägg en <b>dold energibricka +</b> på fastigheten.",
    "energi_minus": "Lägg en <b>dold energibricka −</b> på fastigheten.",
    "direkt_dn_plus": "<b>+1 driftnetto</b> direkt och permanent.",
    "direkt_dn_minus": "<b>−1 driftnetto</b> direkt och permanent.",
    "underhallsvarning": "<b>Underhållsvarning.</b> Lägg kortet öppet på fastigheten och röj den i marknaden för "
                         "<b>{v} Mkr</b>. Tre oröjda: −1 driftnetto och uppgraderingsstopp.",
    "engangskassa_plus": "<b>+{v} Mkr</b> vid nästa marknad.",
    "engangskassa_minus": "<b>−{v} Mkr</b> vid nästa marknad.",
    "inget": "Ingen effekt.",
    "typbred_dn_plus": "<b>+1 driftnetto</b> på allas fastigheter av typen.",
    "typbred_dn_minus": "<b>−1 driftnetto</b> på allas fastigheter av typen.",
    "typbred_ek_plus": "<b>+1 energiklass</b> på allas fastigheter av typen.",
    "typbred_ek_minus": "<b>−1 energiklass</b> på allas fastigheter av typen.",
    "spotlight": "Alla drar <b>ett extra händelsekort</b> per fastighet av typen.",
    "resurs": "Alla med typen drar <b>ett nätverkskort</b>.",
    "villkorat": "Fastigheter av typen med energiklass D eller sämre: <b>−1 driftnetto</b>.",
    "kvartal_dd": "Alla med typen drar <b>ett DD-kort</b> dolt på en fastighet av typen.",
    "kvartal_kassa_minus": "Varje ägare av typen betalar <b>{v} Mkr</b> vid nästa marknad.",
}
REGEL_I_TEXTEN = {"villkorskort", "forkop", "utveckling", "riskbuffert", "natverkskort_fokus"}


def kub(bokstav):
    return f'<span class="kub" style="background:{KUB[bokstav]}"></span>'


def sektion(rubrik, skede, extra=""):
    farg = SKEDE[skede]
    return (f'<div class="p-sektion {extra}" style="color:{farg};border-color:{farg}">'
            f'{bricka(skede, farg)}<span>{rubrik}</span></div>')


def e(t):
    return html.escape(str(t if t is not None else ""))


def bild(namn):
    fil = BILDER / f"{namn}.jpg"
    return fil.as_uri() if fil.exists() else ""


def tal(v):
    s = str(v if v is not None else "").replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


def torn(farg):
    """Den lilla tornsymbolen i hörnet (som på de tryckta korten)."""
    return (f'<svg class="torn" viewBox="0 0 20 40"><g fill="none" stroke="{farg}" stroke-width="1.1">'
            '<path d="M10 2 L2 14 V38 M10 2 L18 14 V38 M10 8 L6 16 V38 M10 8 L14 16 V38 M10 14 V38"/></g></svg>')


def bricka(bokstav, farg):
    return f'<div class="bricka" style="background:{farg}">{bokstav}</div>'


def sexkant(url, farg):
    innehall = f'<img src="{url}">' if url else f'<div class="tom" style="background:{farg}"></div>'
    return f'<div class="sexkant">{innehall}</div>'


# ---------------------------------------------------------------------------- Förvaltning, 58 × 88
def f_framsida(rubrik, undertitel, bildnamn=None, symbol=None):
    """Bildsidan: rosa, F-bricka, rubrik, sexkantsbild, typ, torn och röd list."""
    mitt = sexkant(bild(bildnamn), F["rod"]) if bildnamn else symbol
    return f'''<div class="kort k58 fram" style="--bg:{F["rosa"]};--accent:{F["rod"]}">
      {bricka("F", F["rod"])}
      <div class="f-rubrik">{e(rubrik)}</div>
      {mitt}
      <div class="f-under">{e(undertitel)}</div>
      {torn(F["rod"])}<div class="list"></div></div>'''


def f_textsida(overrad, rubrik, stamning, regel, fot, id_):
    return f'''<div class="kort k58 text" style="--bg:{F["kram"]};--accent:{F["rod"]}">
      <div class="topp">{bricka("F", F["rod"])}<span class="overrad">{e(overrad)}</span></div>
      <div class="t-rubrik">{e(rubrik)}</div>
      {f'<div class="stamning">{e(stamning)}</div>' if stamning else ''}
      <div class="regel">{regel}</div>
      <div class="fot"><span>{e(fot)}</span><span>{e(id_)}</span></div><div class="list"></div></div>'''


def handelsekort(k):
    regel = e(k["Beskrivning"]) if k["Effekt"] in REGEL_I_TEXTEN else REGEL[k["Effekt"]].format(v=tal(k["Värde"]))
    stamning = None if k["Effekt"] in REGEL_I_TEXTEN else k["Beskrivning"]
    fram = f_framsida("Händelsekort", k["Typ"].capitalize(), TYPBILD.get(k["Typ"]))
    text = f_textsida(f"Händelsekort · {k['Typ'].lower()}", k["Rubrik"], stamning, regel,
                      "Läs · lägg · blanda om", k["ID"])
    return fram, text


NATVERK_SYMBOL = '''<div class="sexkant natverk"><svg viewBox="0 0 100 100"><g stroke="#FCF6EF" stroke-width="3">
  <line x1="30" y1="35" x2="70" y2="30"/><line x1="30" y1="35" x2="45" y2="70"/><line x1="70" y1="30" x2="45" y2="70"/>
  <line x1="70" y1="30" x2="78" y2="65"/><line x1="45" y1="70" x2="78" y2="65"/></g>
  <g fill="#FCF6EF"><circle cx="30" cy="35" r="7"/><circle cx="70" cy="30" r="8"/><circle cx="45" cy="70" r="9"/>
  <circle cx="78" cy="65" r="6"/></g></svg></div>'''


def natverkskort(k):
    fram = f_framsida("Nätverkskort", "Förvaltning", symbol=NATVERK_SYMBOL)
    text = f_textsida("Nätverkskort", k["Rubrik"], k.get("Stämning"), e(k["Beskrivning"]),
                      "Max sex på handen", k["ID"])
    return fram, text


KVARTAL = {"HYRESRÄTT": 1, "LOKAL": 2, "KONTOR": 3, "FÖRSKOLA": 4}   # som tryckt på F-brädet


def dela(text):
    """'Stämning. Regel …' -> (stämning, regel): första meningen är stämning, resten regel."""
    t = str(text or "").strip()
    i = t.find(". ")
    return (t[:i + 1], t[i + 2:]) if 0 < i < len(t) - 2 else (None, t)


def kvartalskort(k):
    q = KVARTAL[k["Typ"]]
    regel = e(k["Beskrivning"]) if k["Effekt"] in REGEL_I_TEXTEN else REGEL[k["Effekt"]].format(v=tal(k["Värde"]))
    stamning = None if k["Effekt"] in REGEL_I_TEXTEN else k["Beskrivning"]
    fram = f_framsida("Kvartalskort", f"Kvartal {q} · {k['Typ'].capitalize()}", f"Kvartal {q}")
    text = f_textsida(f"Kvartal {q} · {k['Typ'].lower()}", k["Rubrik"], stamning, regel, "Träffar allas fastigheter av typen", k["ID"])
    return fram, text


def omvarldskort(k):
    stamning, regel = dela(k["Beskrivning"])
    fram = f_framsida("Omvärldskort", "Träffar alla", "Omvärldskort Omvärld")
    text = f_textsida("Omvärldskort", k["Rubrik"], stamning, e(regel), "Ett per kvartal", k["ID"])
    return fram, text


def ddkort(k):
    stamning, regel = dela(k["Beskrivning"])
    fram = f_framsida("Due diligence", "Dras vid köp", "Due Diligence")
    text = f_textsida("DD-kort · läggs dolt", k["Rubrik"], stamning, e(regel), "Ett per köpt fastighet", k["ID"])
    return fram, text


def fs_kort(k, senior=False):
    sida = "Senior" if senior else "Junior"
    ruta = f'<div class="egenskap"><span>{"Senior" if senior else "Förmåga"}</span>{e(k["Senior"] if senior else k["Junior"])}</div>'
    return f'''<div class="kort k58 text" style="--bg:{F["kram"]};--accent:{F["rod"]}">
      <div class="topp">{bricka("F", F["rod"])}<span class="overrad">Förvaltningsstöd · {sida}</span></div>
      <div class="fc-huvud">{sexkant(bild(PERSONBILD.get(k["ID"], "")), F["rod"])}
        <div><div class="t-rubrik">{e(k["Namn"])}</div></div></div>
      <div class="stamning">{e(k["Beskrivning"])}</div>
      {ruta}
      <div class="fot"><span>{"Vänd vid två utvecklingsbrickor" if not senior else "Senior"}</span><span>{e(k["ID"])}</span></div>
      <div class="list"></div></div>'''


def fc_kort(k, senior=False):
    """FC: dubbelsidigt, junior på ena sidan och senior på den andra."""
    sida = "Senior" if senior else "Junior"
    rader = [("Styrka", k["Senior"])] if senior else [("Styrka", k["Junior_styrka"]), ("Svaghet", k["Junior_svaghet"])]
    ruta = "".join(f'<div class="egenskap"><span>{e(a)}</span>{e(b)}</div>' for a, b in rader)
    return f'''<div class="kort k58 text" style="--bg:{F["kram"]};--accent:{F["rod"]}">
      <div class="topp">{bricka("F", F["rod"])}<span class="overrad">Fastighetschef · {sida}</span></div>
      <div class="fc-huvud">{sexkant(bild(PERSONBILD.get(k["Namn"], "")), F["rod"])}
        <div><div class="t-rubrik">{e(k["Namn"])}</div><span class="etikett">{e(k["Typ"].capitalize())}</span></div></div>
      <div class="stamning">{e(k["Beskrivning"])}</div>
      {ruta}
      <div class="fot"><span>{"Vänd vid två utvecklingsbrickor" if not senior else "Senior"}</span><span>{e(k["ID"])}</span></div>
      <div class="list"></div></div>'''


# ---------------------------------------------------------------------------- Projektkort, 88 × 146
def projekt_framsida(p):
    mork, ljus = TYPFARG[p["Typ"]]
    return f'''<div class="kort k88 fram projekt" style="--bg:{ljus};--accent:{mork}">
      <div class="p-skede">{bricka("PU", SKEDE["PU"])}</div>
      <div class="p-typ">{e(p["Typ"])}</div>
      <div class="p-namn">{e(p["Kortnamn"])}</div>
      <div class="p-hq">{kub("H")}H {e(tal(p["Hållbarhetskrav H"]))}{kub("Q")}Q {e(tal(p["Kvalitetskrav Q"]))}</div>
      {sexkant(bild(f'{BILDPREFIX[p["Typ"]]} {p["Kortnamn"]}'), mork)}
      <div class="p-besk">{e(p["Beskrivning"])}</div>
      <table class="p-tal">
        <tr><td>BTA</td><td>{e(tal(p["BTA (kvm)"]))} kvm</td></tr>
        <tr><td>Utvecklingskostnad</td><td>{e(tal(p["Utvecklingskostnad (Mkr)"]))} Mkr</td></tr>
        <tr><td>Anskaffning</td><td>{e(tal(p["Anskaffning (Mkr)"]))} Mkr</td></tr></table>
      <div class="list"></div></div>'''


def projekt_textsida(p):
    """Baksidan: planering (som tryckt) och den nya förvaltningsdelen."""
    mork, ljus = TYPFARG[p["Typ"]]
    niva = [(k.replace("Nivåkrav ", ""), p[k]) for k in p if k and k.startswith("Nivåkrav ")]
    nivarader = "".join(f'<tr><td>{e(n)}</td><td>{e(v if v not in (None, "-") else "–")}</td></tr>' for n, v in niva)
    plan = [("BTA", f'{tal(p["BTA (kvm)"])} kvm'), ("Utvecklingskostnad", f'{tal(p["Utvecklingskostnad (Mkr)"])} Mkr'),
            ("Anskaffning", f'{tal(p["Anskaffning (Mkr)"])} Mkr'), ("Riskbuffert", tal(p["Riskbuffert"]) or "–"),
            ("Passera nämnden", f'+{tal(p["Passera nämnden (>)"])}'),
            (f'{kub("H")}Hållbarhetskrav', tal(p["Hållbarhetskrav H"])), (f'{kub("Q")}Kvalitetskrav', tal(p["Kvalitetskrav Q"]))]
    planrader = "".join(f"<tr><td>{a}</td><td>{e(b)}</td></tr>" for a, b in plan)
    if p["Typ"] == "BRF":
        forv = f'''{sektion("Försäljning", "G")}
          <table class="p-tal"><tr><td>Marknadsvärde</td><td>{e(tal(p["Marknadsvärde (Mkr)"]))} Mkr</td></tr></table>
          <div class="p-regel">{e(p["Rörligt marknadsvärde"])}</div>'''
    else:
        forv = f'''{sektion("Förvaltning", "F")}
          <table class="p-tal stor">
            <tr><td>Driftnetto</td><td>{e(tal(p["Driftnetto (Mkr/år)"]))} Mkr/år</td></tr>
            <tr><td>Räntekostnad</td><td>{e(tal(p["Räntekostnad (Mkr/år)"]))} Mkr/år</td></tr>
            <tr><td>Lån</td><td>{e(tal(p["Lån (Mkr)"]))} Mkr</td></tr>
            <tr><td>Marknadsvärde</td><td>{e(tal(p["Marknadsvärde (Mkr)"]))} Mkr</td></tr>
            <tr><td>Energiklass</td><td><span class="ek">{e(p["Energiklass"])}</span></td></tr></table>
          <div class="p-regel">Marknadsvärde = (driftnetto + ränta) ÷ yield.<br>
            Marknadsvärde under lånet → tvångsförsäljning.</div>'''
    return f'''<div class="kort k88 text projekt" style="--bg:{ljus};--accent:{mork}">
      <div class="p-namn vanster">{e(p["Namn"])}</div>
      <div class="p-kolumner">
        <div>{sektion("Projektutveckling", "PU")}<table class="p-tal">{planrader}</table>
             {sektion("Planering", "PL", "liten")}
             <table class="p-tal"><tr><td>{kub("T")}Tidspåverkan</td><td>{e(tal(p["Tidspåverkan T"]) or "–")}</td></tr></table>
             <div class="p-underrubrik">Nivåkrav leverantörer</div><table class="p-tal liten">{nivarader}</table></div>
        <div>{forv}</div></div>
      <div class="fot"><span>Behåll kortet så länge ni äger projektet</span><span>{e(p["Kort-id"])}</span></div>
      <div class="list"></div></div>'''
