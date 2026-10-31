// farglagg_projektkort.jsx v27 FAST
//
// Nytt i v26:
//   - _bakskede_<vad>     : fylls med bakskede-färg (ljusare variant
//                           av skede_color, motsvarar 15 % opacitet
//                           över vitt). Datapunkt: _bakskede_color
//                           (CSV-kolumn: bakskede). Skickas till bakgrunden
//                           på kortets framsida.
//
// Nytt i v25:
//   - Allt inuti en _keep_*-grupp hoppas över helt. Bekvämt för
//     bildramar och andra grupperade element som inte ska röras.
//
//
// Nytt i v24:
//   - _nobrf_<vad>        : döljs (visible=false) om kortets _typ = "BRF"
//   - _bta_<vad>          : fylls med BTA-färg (#7A6420)
//   - _bya_<vad>          : fylls med BYA-färg (#2F3D44)
//   - _BxA_<vad>          : fylls med BTA- eller BYA-färg baserat på
//                           _beror_av-datapunkten (eller elementets
//                           eget textinnehåll som fallback)
//   - _niv_<N> / niv_<N>  : ring som fylls om N <= nivå-nummer
//                           (från _niv eller _skede_nivå datapunkt)
//   - _exemplar_<vad>     : skriver in global EXEMPLAR_NR (1..N) eller "X"
//                           om variabeln inte är satt. _exemplar_spelare
//                           rörs INTE (spelarens namn).
//   - Detekterar dominant axel (x eller y) automatiskt — fungerar
//     nu även för vertikalt staplade kort (t.ex. 1x8 layout).
//
// Nytt i v23:
//   - Stöd för multi-record Data Merge där FLERA kort ligger på SAMMA
//     spread. Varje kort har sin egen uppsättning _klass, _linecolor,
//     _fillcolor m.m. (replikerade via Data Merge).
//
// Nytt i v22: opt-in istället för opt-out. Element lämnas orörda om de
//   inte är namngivna enligt konventionen.
//
// NAMNKONVENTION:
//   _line_<vad>         -> stroke = line_color (kategori-färg)
//   _fill_<vad>         -> fill   = line_color
//   _line_fill_<vad>    -> både stroke och fill = line_color
//   _text_<vad>         -> textfärg = line_color
//   _bta_<vad>          -> fill = #7A6420 (BTA-färg)
//   _bya_<vad>          -> fill = #2F3D44 (BYA-färg)
//   _BxA_<vad>          -> fill = BTA eller BYA beroende på _beror_av
//   _ejBRF_<vad>        -> visible = false om _typ = "BRF"
//   (_nobrf_<vad>       -> samma som _ejBRF_, äldre namn, stöds fortfarande)
//   _ejFC_<vad>         -> visible = false om _mildring_roll = "–"
//                          (på F_händelsekort: ingen roll tilldelad)
//   _niv_<N> / niv_<N>  -> ring; fylls om N <= nivå, annars tom
//   A_bar..D_bar        -> stapel-logik (opacitet per klass)
//   A_*..D_* (ej _bar)  -> klass-logik (fill/text växlar mellan vit/line)
//   _F1..._FN           -> steg-indikator
//   _skede_<vad>        -> fas-färg
//   _bakskede_<vad>     -> ljusare fas-färg (bakgrund på framsidan)
//
// DATAPUNKTER (textramar — innehåll fylls via Data Merge):
//   _fillcolor, _linecolor, _skede_color, _bakskede_color  -> hex-värden (#RRGGBB)
//   _klass                                -> bokstav A/B/C/D
//   _steg                                 -> heltal
//   _typ                                  -> text (t.ex. "BRF", "AB")
//   _beror_av                             -> "BTA" eller "BYA"
//   _niv  (eller _skede_nivå)             -> heltal (nivå-nummer)
//   _mildring_roll                        -> roll-text eller "–" (ingen)
//
// Nytt i v22 behållet: typsnitt är opt-in. Bara textramar namngivna
//   _font_rubrik eller _font_brod får font-bytet. Allt annat behåller
//   sitt typsnitt från InDesign-filen.

// ── Fallback-färger för _bta_/_bya_/_BxA_ ─────────────────────────────
// Sedan v23 läses fill_color primärt från _fillcolor-datapunkten på
// samma kort (datamerge från CSV). BTA_HEX/BYA_HEX används bara som
// fallback om kortet saknar _fillcolor-textframe — t.ex. på äldre
// mallar eller tomma testkort.
var BTA_HEX = "#7A4F20";
var BYA_HEX = "#2F3D44";

var doc = app.activeDocument;
var uppdaterade = 0;
var ej_matchade = 0;
var arBildsida = doc.name.toLowerCase().indexOf("bildsida") > -1;

var DEBUG_LINJER = [];
// I batchläge (TYST=true) ska vi INTE bygga enorm debug-logg i minnet.
// Vill du felsöka färgläggningen separat: kör skriptet direkt, eller sätt
// FARG_DEBUG = true innan doScript.
if (typeof FARG_DEBUG === "undefined") {
    FARG_DEBUG = (typeof TYST === "undefined");
}
var FARG_DEBUG_MAX_RADER = 3000;
function debugLog(rad) {
    if (!FARG_DEBUG) return;
    if (DEBUG_LINJER.length < FARG_DEBUG_MAX_RADER) {
        DEBUG_LINJER.push(rad);
    } else if (DEBUG_LINJER.length === FARG_DEBUG_MAX_RADER) {
        DEBUG_LINJER.push("... debug-logg kapad vid " + FARG_DEBUG_MAX_RADER + " rader ...");
    }
}

var TYPSNITT = lasTypsnittConfig();
var SKEDE_FALLBACK_HEX = harledSkedeHexFranDocNamn(doc.name);

// ── Namnmatchare ──────────────────────────────────────────────────────
function klassPrefix(namn) {
    if (!namn) return null;
    if (/^[A-D]_/.test(namn)) return namn.charAt(0);
    return null;
}
function stegNummer(namn) {
    if (!namn) return null;
    // Matchar _F<N> (rent segment) eller _F<N>_<suffix> (t.ex. _F1_siffra)
    var m = namn.match(/^_F(\d+)(_.*)?$/);
    return m ? parseInt(m[1], 10) : null;
}

// Returnerar true om namnet ÄR ett rent steg-segment (utan suffix).
// _F1 = segment, _F1_siffra = annat element.
function arRentStegSegment(namn) {
    return namn && /^_F\d+$/.test(namn);
}
function arLineFill(namn)   { return namn && namn.indexOf("_line_fill_") === 0; }
function arLineEndast(namn) { return namn && namn.indexOf("_line_") === 0 && !arLineFill(namn); }
function arFillEndast(namn) { return namn && namn.indexOf("_fill_") === 0; }
function arTextFarg(namn)   { return namn && namn.indexOf("_text_") === 0; }
function arSkede(namn)      { return namn && namn.indexOf("_skede_") === 0; }
// Accepterar både _ejBRF_ (konsekvent med _ejFC_) och _nobrf_ (äldre namn)
function arNobrf(namn) {
    return namn && (namn.indexOf("_ejBRF_") === 0 || namn.indexOf("_nobrf_") === 0);
}

// Returnerar true om elementet ligger inuti en grupp/ram vars namn börjar
// med "_keep_". Allt inuti en sådan grupp skyddas från färgläggning —
// bekvämt för bildramar, logotyper, etc. som aldrig ska röras.
function arInutiKeepGrupp(item) {
    try {
        var p = item.parent;
        while (p) {
            if (p instanceof Spread || p instanceof Page ||
                p instanceof Document) break;
            var pNamn = "";
            try { pNamn = p.name || ""; } catch(e) {}
            if (pNamn.indexOf("_keep_") === 0) return true;
            p = p.parent;
        }
    } catch(e) {}
    return false;
}
function arEjFC(namn)       { return namn && namn.indexOf("_ejFC_") === 0; }
function arBta(namn)        { return namn && namn.indexOf("_bta_") === 0; }
function arBya(namn)        { return namn && namn.indexOf("_bya_") === 0; }
function arBxA(namn)        { return namn && namn.indexOf("_BxA_") === 0; }
// _bakgrund_<vad>: fylls med bakgrund_color (solid, 100% opacitet).
// OBS: namnet "_bakgrund_color" är datapunkten och matchar INTE här.
function arBakgrund(namn) {
    return namn && namn.indexOf("_bakgrund_") === 0 && namn !== "_bakgrund_color";
}
// _bakskede_<vad>: fylls med bakskede-färg (ljusare variant av skede,
// motsvarande 15% opacitet över vitt). Datapunkt: _bakskede_color.
// Skickas till bakgrunden så övriga element ligger ovanpå.
function arBakskede(namn) {
    return namn && namn.indexOf("_bakskede_") === 0 && namn !== "_bakskede_color";
}
// Matchar _exemplar_* men INTE _exemplar_spelare (som är spelarens namn)
function arExemplar(namn) {
    return namn && namn.indexOf("_exemplar_") === 0 && namn !== "_exemplar_spelare";
}

// Matchar _niv_<N> eller niv_<N> (stödjer båda stavningarna)
function nivNummer(namn) {
    if (!namn) return null;
    var m = namn.match(/^_?niv_(\d+)$/);
    return m ? parseInt(m[1], 10) : null;
}

function extraheraKlass(raText) {
    if (!raText) return null;
    var m = raText.match(/[A-Da-d]/);
    return m ? m[0].toUpperCase() : null;
}
function extraheraSteg(raText) {
    if (!raText) return null;
    var m = raText.match(/\d+/);
    return m ? parseInt(m[0], 10) : null;
}
// Returnerar "BTA", "BYA" eller null från en text
function extraheraBxA(raText) {
    if (!raText) return null;
    if (/BTA/i.test(raText)) return "BTA";
    if (/BYA/i.test(raText)) return "BYA";
    return null;
}

// ── Mittpunkt för ett objekt (geometricBounds = [y1, x1, y2, x2]) ────
function mittpunkt(item) {
    try {
        var gb = item.geometricBounds;
        return { x: (gb[1] + gb[3]) / 2, y: (gb[0] + gb[2]) / 2 };
    } catch(e) {
        return null;
    }
}

function avstand(p1, p2) {
    if (!p1 || !p2) return Number.MAX_VALUE;
    var dx = p1.x - p2.x, dy = p1.y - p2.y;
    return Math.sqrt(dx * dx + dy * dy);
}

// ── Hitta närmaste datapunkt i en lista ─────────────────────────────
function narmaste(item, datapunkter) {
    var min_p = null;
    var min_d = Number.MAX_VALUE;
    var itemMid = mittpunkt(item);
    if (!itemMid) return null;
    for (var i = 0; i < datapunkter.length; i++) {
        var d = avstand(itemMid, datapunkter[i].mid);
        if (d < min_d) {
            min_d = d;
            min_p = datapunkter[i];
        }
    }
    return min_p;
}

// ── Kort-bands-matchning: sortera datapunkter efter dominant axel
//    (x ELLER y) och välj det band som elementet faller inom.
//    Robustare än närmaste-granne när ett kort är brett/högt och
//    datapunkten ligger i ett hörn av kortet.
function bandsMatch(item, sorteradeDatapunkter, kortStorlek, axel) {
    var itemMid = mittpunkt(item);
    if (!itemMid) return null;
    if (sorteradeDatapunkter.length === 0) return null;
    if (sorteradeDatapunkter.length === 1) return sorteradeDatapunkter[0];
    if (!kortStorlek || kortStorlek === 0) {
        // Fallback: närmaste-granne om kort-storleken inte gick att räkna ut
        return narmaste(item, sorteradeDatapunkter);
    }

    // Räkna ut vilket kort-index elementet tillhör baserat på dominant axel
    var forstaDatapunkt = sorteradeDatapunkter[0].mid[axel];
    var kortIndex = Math.round((itemMid[axel] - forstaDatapunkt) / kortStorlek);
    if (kortIndex < 0) kortIndex = 0;
    if (kortIndex >= sorteradeDatapunkter.length) kortIndex = sorteradeDatapunkter.length - 1;
    return sorteradeDatapunkter[kortIndex];
}

// ── Sortera en datapunkt-lista efter vald axel (x eller y) ───────────
function sorteraEfterAxel(datapunkter, axel) {
    return datapunkter.slice().sort(function(a, b) {
        return a.mid[axel] - b.mid[axel];
    });
}

// ── Räkna ut kort-storlek från sorterad datapunkt-lista ──────────────
//    Hittar minsta positiva delta mellan intilliggande sorterade
//    datapunkter — viktigt för 4×2-layouter där första två sorterade
//    kort har SAMMA x-värde (och delta=0 skulle ge fel resultat).
function kortStorlekFran(sorteradeDatapunkter, axel) {
    if (sorteradeDatapunkter.length < 2) return 1000;  // bara ett kort = jättestort band
    var minDelta = Infinity;
    for (var i = 1; i < sorteradeDatapunkter.length; i++) {
        var d = sorteradeDatapunkter[i].mid[axel] - sorteradeDatapunkter[i-1].mid[axel];
        if (d > 0 && d < minDelta) minDelta = d;
    }
    return minDelta === Infinity ? 1000 : minDelta;
}

// ── Detektera dominant axel: om datapunkterna varierar mer i y-led
//    än x-led är korten staplade vertikalt, då band-matchar vi i y.
function dominantAxis(datapunkter) {
    if (datapunkter.length < 2) return "x";
    var xMin = Infinity, xMax = -Infinity;
    var yMin = Infinity, yMax = -Infinity;
    for (var i = 0; i < datapunkter.length; i++) {
        var p = datapunkter[i].mid;
        if (p.x < xMin) xMin = p.x;
        if (p.x > xMax) xMax = p.x;
        if (p.y < yMin) yMin = p.y;
        if (p.y > yMax) yMax = p.y;
    }
    return (yMax - yMin) > (xMax - xMin) ? "y" : "x";
}

// ── Huvudloop: ett spread kan innehålla flera kort ───────────────────
for (var p = 0; p < doc.spreads.length; p++) {
    var spread = doc.spreads[p];
    var sida   = spread.pages[0];

    // ── Steg 1: Samla alla datapunkter på spreaden ──────────────────
    // Multi-record merge kan ge flera av varje (t.ex. 4 _klass).
    var klassPunkter     = [];  // {mid, klass}
    var linePunkter      = [];  // {mid, hex}
    var fillPunkter      = [];  // {mid, hex}
    var skedePunkter     = [];  // {mid, hex}
    var bakskedePunkter  = [];  // {mid, hex}
    var bakgrundPunkter  = [];  // {mid, hex}
    var stegPunkter      = [];  // {mid, steg}
    var typPunkter       = [];  // {mid, typ}     t.ex. "BRF", "AB"
    var nivPunkter       = [];  // {mid, niv}     heltal
    var berorAvPunkter   = [];  // {mid, typ}     "BTA" eller "BYA"
    var mildringPunkter  = [];  // {mid, roll}    Mildring_roll — "–" = ingen roll

    var allItems = spread.allPageItems;
    for (var i = 0; i < allItems.length; i++) {
        var it = allItems[i];
        if (!(it instanceof TextFrame)) continue;
        var raw = "";
        try { raw = it.contents; } catch(e) { continue; }
        var text = raw.replace(/[\s\r\n]+/g, "");
        var namn = "";
        try { namn = it.name || ""; } catch(e) {}
        var mid = mittpunkt(it);
        if (!mid) continue;

        // arDatapunkt = "ren automatiserings-datapunkt" — göms direkt så de
        // inte syns i PDF:en. _skede_nivå är visuellt synligt ("NIVÅ 3") och
        // göms INTE, även om vi läser nivå-numret därifrån.
        var arDatapunkt = false;

        if (/^#[0-9A-Fa-f]{6}$/.test(text)) {
            if      (namn === "_linecolor")      { linePunkter.push({mid: mid, hex: text}); arDatapunkt = true; }
            else if (namn === "_fillcolor")      { fillPunkter.push({mid: mid, hex: text}); arDatapunkt = true; }
            else if (namn === "_skede_color")    { skedePunkter.push({mid: mid, hex: text}); arDatapunkt = true; }
            else if (namn === "_bakskede_color") { bakskedePunkter.push({mid: mid, hex: text}); arDatapunkt = true; }
            else if (namn === "_bakgrund_color") { bakgrundPunkter.push({mid: mid, hex: text}); arDatapunkt = true; }
        }
        if (namn === "_klass") {
            var k = extraheraKlass(raw);
            if (k) klassPunkter.push({mid: mid, klass: k});
            arDatapunkt = true;
        }
        if (namn === "_steg") {
            var s = extraheraSteg(raw);
            if (s !== null) stegPunkter.push({mid: mid, steg: s});
            arDatapunkt = true;
        }
        if (namn === "_typ") {
            typPunkter.push({mid: mid, typ: text});
            arDatapunkt = true;
        }
        // _niv är ren datapunkt. _skede_nivå är synligt text-element (t.ex.
        // "NIVÅ 3") så bara läs, göm inte.
        if (namn === "_niv") {
            var nv = extraheraSteg(raw);
            if (nv !== null) nivPunkter.push({mid: mid, niv: nv});
            arDatapunkt = true;
        }
        if (namn === "_skede_niv\u00e5" || namn === "_skede_niv") {
            var nv2 = extraheraSteg(raw);
            if (nv2 !== null) nivPunkter.push({mid: mid, niv: nv2});
            // göms INTE
        }
        if (namn === "_beror_av") {
            var bx = extraheraBxA(raw);
            if (bx) berorAvPunkter.push({mid: mid, typ: bx});
            arDatapunkt = true;
        }
        if (namn === "_mildring_roll") {
            mildringPunkter.push({mid: mid, roll: text});
            arDatapunkt = true;
        }

        // Dölj rena datapunkter så de inte syns i slutliga PDF:en.
        // Skriptet kan ändå läsa dem i kommande iterationer (osynliga
        // items finns fortfarande i allPageItems).
        if (arDatapunkt) {
            try { it.visible = false; } catch(e) {}
        }
    }

    debugLog("Spread " + p + ": " + klassPunkter.length + " _klass, " +
             linePunkter.length + " _linecolor, " +
             fillPunkter.length + " _fillcolor, " +
             stegPunkter.length + " _steg, " +
             skedePunkter.length + " _skede_color, " +
             bakskedePunkter.length + " _bakskede_color, " +
             typPunkter.length + " _typ, " +
             nivPunkter.length + " _niv, " +
             berorAvPunkter.length + " _beror_av, " +
             mildringPunkter.length + " _mildring_roll");

    // Logg varje klass-värde
    for (var ki = 0; ki < klassPunkter.length; ki++) {
        debugLog("  _klass @ (" + Math.round(klassPunkter[ki].mid.x) + "," +
                 Math.round(klassPunkter[ki].mid.y) + ") = " + klassPunkter[ki].klass);
    }

    // ── Välj dominant axel (x eller y) baserat på den lista med flest
    //    datapunkter — horisontell layout = x, vertikal = y.
    var axelKandidater = [klassPunkter, linePunkter, fillPunkter];
    var axelBaslista = linePunkter;
    for (var ak = 0; ak < axelKandidater.length; ak++) {
        if (axelKandidater[ak].length > axelBaslista.length) {
            axelBaslista = axelKandidater[ak];
        }
    }
    var axel = dominantAxis(axelBaslista);

    // ── Sortera datapunkter efter dominant axel för bands-matchning ─
    var klassSort    = sorteraEfterAxel(klassPunkter, axel);
    var lineSort     = sorteraEfterAxel(linePunkter, axel);
    var fillSort     = sorteraEfterAxel(fillPunkter, axel);
    var skedeSort    = sorteraEfterAxel(skedePunkter, axel);
    var bakskedeSort = sorteraEfterAxel(bakskedePunkter, axel);
    var bakgrundSort = sorteraEfterAxel(bakgrundPunkter, axel);
    var stegSort     = sorteraEfterAxel(stegPunkter, axel);
    var typSort      = sorteraEfterAxel(typPunkter, axel);
    var nivSort      = sorteraEfterAxel(nivPunkter, axel);
    var berorAvSort  = sorteraEfterAxel(berorAvPunkter, axel);
    var mildringSort = sorteraEfterAxel(mildringPunkter, axel);

    // Räkna ut kort-storlek för klass/line/fill/skede-matchning (baserat
    // på den lista med flest element som inte är steg).
    var kandidatListor = [klassSort, lineSort, fillSort];
    var baslista = null;
    var maxAntal = 1;
    for (var kl = 0; kl < kandidatListor.length; kl++) {
        if (kandidatListor[kl].length > maxAntal) {
            maxAntal = kandidatListor[kl].length;
            baslista = kandidatListor[kl];
        }
    }
    var kortStorlek = baslista ? kortStorlekFran(baslista, axel) : 1000;
    debugLog("  Axel: " + axel + ", Kort-storlek: " + Math.round(kortStorlek) +
             " (baserat p\u00e5 " + maxAntal + " referenspunkter)");

    // ── Förbygg map från varje _F-element till rätt _steg-datapunkt ──
    // Rank-matchning per element-typ: sortera alla _F1 efter x, alla
    // _F1_siffra efter x, alla _F2 efter x osv. Matcha index-för-index
    // mot _steg-datapunkterna.
    var stegMap = {};  // itemId -> stegDatapunkt
    var alltSteg = stegSort;
    if (alltSteg.length > 0) {
        // Samla per (N, suffix): t.ex. "1:segment", "1:_siffra", "2:segment", ...
        var stegElementPerKey = {};
        for (var si = 0; si < allItems.length; si++) {
            var sitem = allItems[si];
            var snamn = "";
            try { snamn = sitem.name || ""; } catch(e) { continue; }
            var m = snamn.match(/^_F(\d+)(.*)$/);
            if (!m) continue;
            var key = m[1] + ":" + (m[2] || "segment");
            if (!stegElementPerKey[key]) stegElementPerKey[key] = [];
            stegElementPerKey[key].push(sitem);
        }
        // För varje key, sortera elementen efter x och mappa till stegSort
        for (var K in stegElementPerKey) {
            var arr = stegElementPerKey[K];
            arr.sort(function(a, b) {
                var am = mittpunkt(a), bm = mittpunkt(b);
                return (am ? am.x : 0) - (bm ? bm.x : 0);
            });
            for (var ai = 0; ai < arr.length && ai < alltSteg.length; ai++) {
                stegMap[arr[ai].id] = alltSteg[ai];
            }
        }
    }
    debugLog("  Stegmap: " + (alltSteg.length > 0 ? "byggd med " + alltSteg.length + " kort" : "tom"));

    // ── DIAGNOSTIK: logga alla UNIKA elementnamn på sidan ──────────
    // Dyrt i stora batchar, så körs bara när FARG_DEBUG=true.
    if (FARG_DEBUG) {
        var uniqeNamn = {};
        var diagItems = allItems;
        for (var di = 0; di < diagItems.length; di++) {
            var dn = "";
            try { dn = diagItems[di].name || ""; } catch(e) {}
            if (dn && !uniqeNamn[dn]) {
                uniqeNamn[dn] = 1;
            } else if (dn) {
                uniqeNamn[dn]++;
            }
        }
        var namnLista = [];
        for (var un in uniqeNamn) {
            namnLista.push(un + " (x" + uniqeNamn[un] + ")");
        }
        debugLog("  Alla unika element-namn: " + namnLista.join(", "));
    }

    // ── Kräver att minst en _linecolor finns ────────────────────────
    if (linePunkter.length === 0) { ej_matchade++; continue; }

    var vitFarg = null;
    try { vitFarg = doc.swatches.itemByName("Paper"); } catch(e) {}
    if (!vitFarg || !vitFarg.isValid) vitFarg = skapaFarg(doc, "#FFFFFF");
    var ingenFarg = null;
    try { ingenFarg = doc.swatches.itemByName("None"); } catch(e) {}

    // ── Steg 2: Färglägg varje element baserat på NÄRMASTE datapunkt ─
    var sidItems = allItems;
    for (var i = 0; i < sidItems.length; i++) {
        var item = sidItems[i];
        var itemNamn = "";
        try { itemNamn = item.name || ""; } catch(e) { continue; }
        if (!itemNamn) continue;

        // Skydda allt inuti _keep_*-grupper från färgläggning.
        // Undantag: _niv_<N>-ringar måste fortfarande färgläggas även om
        // de ligger i en _keep_-grupp (nivå-sektionen grupperas ofta så).
        if (arInutiKeepGrupp(item)) {
            if (nivNummer(itemNamn) !== null) {
                debugLog("  KEEP-OVERRIDE (niv): " + itemNamn);
                // Falla igenom till niv-hanteringen nedan
            } else {
                if (arNobrf(itemNamn) || arEjFC(itemNamn)) {
                    debugLog("  SKIPPED (inuti _keep_-grupp): " + itemNamn);
                }
                continue;
            }
        }

        try {
            // ── Hitta närmaste line/fill/skede/klass/steg för detta element ──
            var narmLine  = bandsMatch(item, lineSort, kortStorlek, axel);
            var narmFill  = bandsMatch(item, fillSort, kortStorlek, axel);
            var narmSkede = bandsMatch(item, skedeSort, kortStorlek, axel);
            var narmKlass = bandsMatch(item, klassSort, kortStorlek, axel);
            var narmSteg  = stegMap[item.id] || null;

            var lineHex = narmLine ? narmLine.hex : null;
            if (!lineHex) continue;  // inget att färglägga med
            var lineFarg = skapaFarg(doc, lineHex);
            // fill_color hex (mörk text/aktiv-bakgrund). Fallback till line
            // om _fillcolor saknas på kortet.
            var fillHex = narmFill ? narmFill.hex : lineHex;
            var fillFarg = (fillHex === lineHex) ? lineFarg : skapaFarg(doc, fillHex);

            // ── Steg-element: _F1, _F2, ..., _FN (+ _F<N>_suffix) ─────
            var stegNr = stegNummer(itemNamn);
            if (narmSteg && stegNr !== null) {
                var stegAktiv = (stegNr <= narmSteg.steg);
                var arSegment = arRentStegSegment(itemNamn);

                if (arSegment) {
                    // Själva segmentet: line_color, opacitet styr aktiv/inaktiv
                    try { item.fillColor = lineFarg; } catch(e) {}
                    try { item.strokeColor = ingenFarg; } catch(e) {}
                    try {
                        item.transparencySettings.blendingSettings.opacity = stegAktiv ? 100 : 50;
                    } catch(e) {}
                } else {
                    // Suffix-element (t.ex. _F5_siffra): endast AKTUELLT steg
                    // visas. Passerade OCH framtida steg raderas helt.
                    if (stegNr !== narmSteg.steg) {
                        try { item.remove(); } catch(e) {}
                    }
                    // aktuellt steg: lämnas orört
                }
                continue;
            }

            // ── Klass-element: A_*, B_*, C_*, D_* ────────────────────
            var elKlass = klassPrefix(itemNamn);
            if (narmKlass && elKlass) {
                var klass = narmKlass.klass;
                var efterUnderstreck = itemNamn.substring(2);
                var arStapel = (efterUnderstreck === "bar");

                var itemMid = mittpunkt(item);
                if (arStapel) {
                    var stapelAktiv = (elKlass <= klass);
                    debugLog("  " + itemNamn + " @ (" +
                             Math.round(itemMid.x) + "," + Math.round(itemMid.y) +
                             ") -> klass=" + klass + " -> " +
                             (stapelAktiv ? "AKTIV (100%)" : "inaktiv (50%)"));
                    try { item.fillColor = vitFarg; } catch(e) {}
                    try { item.strokeColor = ingenFarg; } catch(e) {}
                    try {
                        item.transparencySettings.blendingSettings.opacity = stapelAktiv ? 100 : 50;
                    } catch(e) {}
                } else {
                    var arValdExakt = (elKlass === klass);
                    var typNamn = (item instanceof TextFrame) ? "text" :
                                  (item instanceof Rectangle) ? "rect" :
                                  (item instanceof Oval) ? "oval" :
                                  (item instanceof Polygon) ? "poly" : "?";
                    debugLog("  " + itemNamn + " [" + typNamn + "] @ (" +
                             Math.round(itemMid.x) + "," + Math.round(itemMid.y) +
                             ") -> klass=" + klass + " -> " +
                             (arValdExakt ? "AKTIV" : "inaktiv"));
                    if (item instanceof TextFrame) {
                        // AKTIV: ramens bakgrund blir line_color, text blir vit.
                        // INAKTIV: lämnas orörd (behåller mallens färger).
                        if (arValdExakt) {
                            var fillFel = null;
                            try {
                                item.fillColor = fillFarg;
                            } catch(e) { fillFel = "fillColor: " + e.message; }
                            try {
                                item.strokeColor = fillFarg;
                            } catch(e) { fillFel = (fillFel || "") + " stroke: " + e.message; }
                            try {
                                item.transparencySettings.blendingSettings.opacity = 100;
                            } catch(e) {}
                            // Text inuti blir vit
                            try {
                                if (item.characters.length > 0) {
                                    item.characters.everyItem().fillColor = vitFarg;
                                }
                            } catch(e) { fillFel = (fillFel || "") + " text: " + e.message; }

                            // Loggning av resultat
                            try {
                                var slutFill = item.fillColor.name || "(null)";
                                if (slutFill !== fillFarg.name) {
                                    debugLog("    VARNING " + itemNamn +
                                             ": fillColor blev '" + slutFill +
                                             "' men ska vara '" + fillFarg.name + "'");
                                }
                            } catch(e) {}
                            if (fillFel) {
                                debugLog("    FEL p\u00e5 " + itemNamn + ": " + fillFel);
                            }
                        }
                    } else if (item instanceof Oval || item instanceof Rectangle || item instanceof Polygon) {
                        // AKTIV: fylls med kategori-färg. INAKTIV: lämnas orörd
                        // (behåller vit/transparent från mallen).
                        if (arValdExakt) {
                            var fillFel = null;
                            try {
                                item.fillColor = fillFarg;
                            } catch(e) {
                                fillFel = "fillColor: " + e.message;
                            }
                            try {
                                item.strokeColor = fillFarg;
                            } catch(e) {
                                fillFel = (fillFel || "") + " strokeColor: " + e.message;
                            }
                            try {
                                item.transparencySettings.blendingSettings.opacity = 100;
                            } catch(e) {
                                fillFel = (fillFel || "") + " opacity: " + e.message;
                            }
                            // Försök också override via explicit RGB-värde som sista utväg
                            try {
                                if (item.fillColor.name && item.fillColor.name !== fillFarg.name) {
                                    debugLog("    VARNING " + itemNamn +
                                             ": fillColor \u00e4r '" + item.fillColor.name +
                                             "' ist\u00e4llet f\u00f6r '" + fillFarg.name + "'");
                                }
                            } catch(e) {}
                            if (fillFel) {
                                debugLog("    FEL p\u00e5 " + itemNamn + ": " + fillFel);
                            }
                        }
                    }
                }
                continue;
            }

            // ── Skede-element: _skede_* ─────────────────────────────
            if (narmSkede && arSkede(itemNamn)) {
                var skedeFarg = skapaFarg(doc, narmSkede.hex);
                if (item instanceof TextFrame) {
                    if (itemNamn === "_skede_text" && item.characters.length > 0) {
                        item.characters.everyItem().fillColor = skedeFarg;
                    }
                } else {
                    if (itemNamn.indexOf("frame") > -1) {
                        item.strokeColor = skedeFarg;
                    } else {
                        item.fillColor = skedeFarg;
                    }
                }
                continue;
            }

            // ── _exemplar_<x>: skriv in exemplarsiffran (1-N) eller "X" ─
            //    Om global EXEMPLAR_NR är satt (master_kortproduktion.jsx)
            //    skrivs den in. Annars lämnas rutan som "X".
            //    Hanterar TextFrame, grupp, och ramar med textram inuti.
            if (arExemplar(itemNamn)) {
                var exemplarText = (typeof EXEMPLAR_NR !== "undefined" &&
                                    EXEMPLAR_NR !== null)
                                 ? String(EXEMPLAR_NR) : "X";
                var satt = false;
                try {
                    if (item instanceof TextFrame) {
                        item.contents = exemplarText;
                        satt = true;
                    } else if (item.textFrames && item.textFrames.length > 0) {
                        // Ram eller grupp med direkt underliggande textram
                        item.textFrames.firstItem().contents = exemplarText;
                        satt = true;
                    } else if (item.allPageItems) {
                        // Djupsök i grupp efter första textram
                        var barn = item.allPageItems;
                        for (var ei = 0; ei < barn.length; ei++) {
                            if (barn[ei] instanceof TextFrame) {
                                try {
                                    barn[ei].contents = exemplarText;
                                    satt = true;
                                    break;
                                } catch(e) {}
                            }
                        }
                    }
                } catch(e) {}
                debugLog("  " + itemNamn + " -> EXEMPLAR_NR=" +
                         (typeof EXEMPLAR_NR === "undefined" ? "undef" : EXEMPLAR_NR) +
                         " text=\"" + exemplarText + "\" " +
                         (satt ? "OK" : "MISSLYCKADES (fel elementtyp?)"));
                continue;
            }

            // ── _nobrf_<x> / _ejBRF_<x>: radera om kortets _typ = "BRF" ─
            //    Radering (istället för visible=false) så PDF-export garanterat
            //    inte inkluderar elementet, oavsett export-preferenser.
            if (arNobrf(itemNamn)) {
                var narmTyp = bandsMatch(item, typSort, kortStorlek, axel);
                var typVarde = narmTyp ? narmTyp.typ : "(ingen _typ hittad)";
                var arBRF = narmTyp && /BRF/i.test(narmTyp.typ);
                debugLog("  " + itemNamn + " -> _typ=\"" + typVarde +
                         "\" -> " + (arBRF ? "RADERA" : "BEHÅLL"));
                if (arBRF) {
                    try { item.remove(); } catch(e) {}
                }
                continue;
            }

            // ── _ejFC_<x>: radera om kortets _mildring_roll saknas ────
            //    På F_händelsekort: ingen mildrings-roll tilldelad.
            //    Matchar allt som bara består av streck/bindestreck/mellanslag,
            //    eller tom sträng. Så "–", "—", "-", "---", "- - -" etc.
            if (arEjFC(itemNamn)) {
                var narmMild = bandsMatch(item, mildringSort, kortStorlek, axel);
                var rollVarde = narmMild ? (narmMild.roll || "") : "(ingen _mildring_roll hittad)";
                // Default: radera (ingen mildring). Behall bara om vi hittar
                // en faktisk roll-text.
                var saknar = true;
                if (narmMild) {
                    var rollText = (narmMild.roll || "");
                    var kvarstar = rollText.replace(/[\s\-\u2013\u2014]+/g, "");
                    if (kvarstar !== "") {
                        saknar = false;
                    }
                }
                debugLog("  " + itemNamn + " -> _mildring_roll=\"" + rollVarde +
                         "\" -> " + (saknar ? "RADERA" : "BEHÅLL"));
                if (saknar) {
                    try { item.remove(); } catch(e) {}
                }
                continue;
            }

            // ── niv_<N> / _niv_<N>: ring fylls om N <= nivå ──────────
            var nivNr = nivNummer(itemNamn);
            if (nivNr !== null) {
                var narmNiv = bandsMatch(item, nivSort, kortStorlek, axel);
                if (narmNiv) {
                    var nivAktiv = (nivNr <= narmNiv.niv);
                    if (nivAktiv) {
                        // Aktiv ring: fylld med line_color
                        try { item.fillColor = lineFarg; } catch(e) {}
                    } else {
                        // Inaktiv ring: bara kontur (ingen fyllning)
                        try { item.fillColor = ingenFarg; } catch(e) {}
                    }
                    // Stroke behålls som mallen har den (line_color eller annat)
                }
                continue;
            }

            // ── _BxA_<x> / _bta_<x> / _bya_<x>: använd fill_color från CSV ──
            //   Tidigare hårdkodade BTA_HEX/BYA_HEX. Nu läses fill_color
            //   från _fillcolor-datapunkten (som datamerge fyller från CSV-
            //   kolumnen fill_color). Det gör att alla typer av indikatorer
            //   följer CSV-mappningens fill_color konsekvent — ändra färg
            //   i färgschema.xlsx, kör uppdatera_färger.py och allt följer.
            //
            //   Fallback till BTA_HEX/BYA_HEX om _fillcolor saknas.
            if (arBxA(itemNamn) || arBta(itemNamn) || arBya(itemNamn)) {
                var narmFillBxA = bandsMatch(item, fillSort, kortStorlek, axel);
                var fyllningHex = null;
                if (narmFillBxA && narmFillBxA.hex) {
                    fyllningHex = narmFillBxA.hex;
                } else if (arBya(itemNamn)) {
                    fyllningHex = BYA_HEX;
                } else {
                    fyllningHex = BTA_HEX;
                }
                if (fyllningHex) {
                    var bxaFarg = skapaFarg(doc, fyllningHex);
                    if (item instanceof TextFrame) {
                        if (item.characters.length > 0) {
                            item.characters.everyItem().fillColor = bxaFarg;
                        }
                    } else {
                        try { item.fillColor = bxaFarg; } catch(e) {}
                    }
                }
                continue;
            }

            // ── _bakskede_<x>: fyll med bakskede-färg (ljusare skede) ──
            //    Datapunkt: _bakskede_color (CSV-kolumn: bakskede). Färgen
            //    motsvarar skede_color renderad vid 15% opacitet över vitt,
            //    men appliceras som SOLID 100%-färg för att undvika
            //    opacitets-stapling. Skickas till bakgrunden så övriga
            //    färglagda element syns ovanpå.
            if (arBakskede(itemNamn)) {
                var narmBak = bandsMatch(item, bakskedeSort, kortStorlek, axel);
                var itemMidBak = mittpunkt(item);
                if (narmBak) {
                    var bakFarg = skapaFarg(doc, narmBak.hex);
                    if (item instanceof TextFrame) {
                        if (item.characters.length > 0) {
                            item.characters.everyItem().fillColor = bakFarg;
                        }
                    } else {
                        try { item.fillColor = bakFarg; } catch(e) {}
                    }
                    try {
                        item.transparencySettings.blendingSettings.opacity = 100;
                    } catch(e) {}
                    try { item.sendToBack(); } catch(e) {}
                    debugLog("  " + itemNamn + " @ (" +
                             (itemMidBak ? Math.round(itemMidBak.x) + "," + Math.round(itemMidBak.y) : "?") +
                             ") -> bakskede=" + narmBak.hex + " [sendToBack]");
                } else {
                    debugLog("  " + itemNamn + " @ (" +
                             (itemMidBak ? Math.round(itemMidBak.x) + "," + Math.round(itemMidBak.y) : "?") +
                             ") -> INGEN _bakskede_color HITTAD");
                }
                continue;
            }

            // ── _bakgrund_<x>: fyll med bakgrund_color (solid, 100%) ──
            //    Ersätter tidigare 10%-opacitet-overlay. Genom att använda
            //    en SOLID förtintad färg undviks opacitets-stapling där
            //    bleed-rektanglar överlappar (master_tryckbart.jsx).
            //    Opacitet tvingas till 100% (mallen kan ha haft 10%).
            if (arBakgrund(itemNamn)) {
                var narmBg = bandsMatch(item, bakgrundSort, kortStorlek, axel);
                var itemMidBg = mittpunkt(item);
                if (narmBg) {
                    var bgFarg = skapaFarg(doc, narmBg.hex);
                    if (item instanceof TextFrame) {
                        if (item.characters.length > 0) {
                            item.characters.everyItem().fillColor = bgFarg;
                        }
                    } else {
                        try { item.fillColor = bgFarg; } catch(e) {}
                    }
                    try {
                        item.transparencySettings.blendingSettings.opacity = 100;
                    } catch(e) {}
                    // Skicka bakåt så andra färglagda element (klass-rutor, staplar,
                    // texter) syns ovanpå bakgrunden. Annars täcker den allt.
                    try { item.sendToBack(); } catch(e) {}
                    debugLog("  " + itemNamn + " @ (" +
                             (itemMidBg ? Math.round(itemMidBg.x) + "," + Math.round(itemMidBg.y) : "?") +
                             ") -> bakgrund=" + narmBg.hex + " [sendToBack]");
                } else {
                    debugLog("  " + itemNamn + " @ (" +
                             (itemMidBg ? Math.round(itemMidBg.x) + "," + Math.round(itemMidBg.y) : "?") +
                             ") -> INGEN _bakgrund_color HITTAD");
                }
                continue;
            }

            // ── _line_fill_<x>: både stroke och fill ────────────────
            if (arLineFill(itemNamn)) {
                try { item.strokeColor = lineFarg; } catch(e) {}
                if (item instanceof TextFrame) {
                    if (item.characters.length > 0) {
                        item.characters.everyItem().fillColor = lineFarg;
                    }
                } else {
                    try { item.fillColor = lineFarg; } catch(e) {}
                }
                continue;
            }

            // ── _line_<x>: bara stroke ──────────────────────────────
            if (arLineEndast(itemNamn)) {
                try { item.strokeColor = lineFarg; } catch(e) {}
                continue;
            }

            // ── _fill_<x>: bara fill ────────────────────────────────
            if (arFillEndast(itemNamn)) {
                if (item instanceof TextFrame) {
                    // TEXT: använd fillFarg (mörk fill_color) — annars
                    // försvinner texten på kort där line_color = bakskede
                    if (item.characters.length > 0) {
                        item.characters.everyItem().fillColor = fillFarg;
                    }
                } else {
                    try { item.fillColor = lineFarg; } catch(e) {}
                }
                continue;
            }

            // ── _text_<x>: textfärg ─────────────────────────────────
            if (arTextFarg(itemNamn) && item instanceof TextFrame) {
                if (item.characters.length > 0) {
                    item.characters.everyItem().fillColor = fillFarg;
                }
                continue;
            }

            // Allt annat: lämna orört
        } catch(e) {}
    }

    // ── Bakgrundsruta på bildsidor (stängd av för multi-record) ─────
    // Om det är multi-record (flera _fillcolor på sidan) gör vi inte
    // en heltäckande bakgrundsruta — den skulle bara täcka ett kort-
    // område korrekt och förstöra resten.
    // Fallback-bakgrund: bara om det INTE finns någon _bakgrund_color-
    // datapunkt på spreaden (ny approach ersätter detta med solida
    // _bakgrund_<x>-rektanglar vid 100% opacitet).
    if (arBildsida && fillPunkter.length === 1 && bakgrundPunkter.length === 0) {
        try {
            var fillFarg = skapaFarg(doc, fillPunkter[0].hex);
            var rect = sida.rectangles.add({
                geometricBounds: sida.bounds,
                fillColor:       fillFarg,
                strokeColor:     ingenFarg,
            });
            rect.sendToBack();
            rect.transparencySettings.blendingSettings.opacity = 10;
        } catch(e) {}
    }

    // ── Typsnitt (opt-in): bara _font_rubrik och _font_brod ─────────
    sattTypsnittOptInItems(allItems, TYPSNITT);

    uppdaterade++;
}

// ── Skriv debug-logg (append) till SPELET 2\loggar\farglagg_debug.txt ───
// Fallbacks: desktop + temp om SPELET 2-mappen inte kan nås.
var loggSokv = null;
var mojligaLoggSokv = [];
try {
    var spelDir = (typeof SPELET2_ROT !== "undefined" && SPELET2_ROT)
        ? new Folder(SPELET2_ROT)
        : File($.fileName).parent.parent;
    // Säkerställ att loggar-undermappen finns
    var loggMapp = new Folder(spelDir.fsName + "/loggar");
    if (!loggMapp.exists) loggMapp.create();
    mojligaLoggSokv.push(spelDir.fsName + "/loggar/farglagg_debug.txt");
} catch(e) {}
try { mojligaLoggSokv.push(Folder.desktop.fsName + "/farglagg_debug.txt"); } catch(e) {}
try {
    var temp = Folder.temp || new Folder("~/temp");
    mojligaLoggSokv.push(temp.fsName + "/farglagg_debug.txt");
} catch(e) {}

if (FARG_DEBUG) {
    for (var li = 0; li < mojligaLoggSokv.length; li++) {
        try {
            var loggFil = new File(mojligaLoggSokv[li]);
            loggFil.open("a");
            loggFil.encoding = "UTF-8";
            loggFil.write("\n=== " + doc.name + " ===\n");
            loggFil.write("Tid: " + new Date().toString() + "\n");
            loggFil.write("Antal spreads: " + doc.spreads.length + "\n");
            for (var i = 0; i < DEBUG_LINJER.length; i++) {
                loggFil.write(DEBUG_LINJER[i] + "\n");
            }
            loggFil.close();
            loggSokv = mojligaLoggSokv[li];
            break;
        } catch(e) {}
    }
}

var sammanfattning = "";
for (var i = 0; i < Math.min(DEBUG_LINJER.length, 40); i++) {
    sammanfattning += DEBUG_LINJER[i] + "\n";
}

if (typeof TYST === "undefined") {
    alert("Klart!\n" +
          "Färgsatte: " + uppdaterade + " sidor\n" +
          "Hittade inte färgkoder: " + ej_matchade + " sidor\n\n" +
          "=== DEBUG ===\n" +
          sammanfattning + "\n" +
          "Debug-logg: " + (loggSokv || "KUNDE INTE SKRIVAS"));
}


// ══════════════════════════════════════════════════════════════════════
//  Hjälpfunktioner
// ══════════════════════════════════════════════════════════════════════

var COLOR_CACHE = {};

function hexTillRgb(hex) {
    hex = hex.replace("#","");
    return [parseInt(hex.substring(0,2),16), parseInt(hex.substring(2,4),16), parseInt(hex.substring(4,6),16)];
}

function skapaFarg(doc, hex) {
    if (!hex) hex = "#000000";
    var key = hex.toUpperCase();
    try {
        if (COLOR_CACHE[key] && COLOR_CACHE[key].isValid) return COLOR_CACHE[key];
    } catch(e0) {}

    var namn = "AUTO_" + hex.replace("#","").toUpperCase();
    try {
        var existing = doc.colors.itemByName(namn);
        if (existing.isValid) {
            COLOR_CACHE[key] = existing;
            return existing;
        }
    } catch(e) {}
    var rgb = hexTillRgb(hex);
    var c = doc.colors.add();
    c.name = namn; c.model = ColorModel.PROCESS; c.space = ColorSpace.RGB;
    c.colorValue = [rgb[0], rgb[1], rgb[2]];
    COLOR_CACHE[key] = c;
    return c;
}

function lasTypsnittConfig() {
    var cfg = {
        rubrik_font: "Minion Pro", rubrik_style: "Bold",
        brodtext_font: "Minion Pro", brodtext_style: "Regular",
        storlek_troskel: 14
    };
    var spelDir;
    if (typeof SPELET2_ROT !== "undefined" && SPELET2_ROT) {
        spelDir = new Folder(SPELET2_ROT);
    } else {
        spelDir = File($.fileName).parent.parent;
    }
    var jsonFil = File(spelDir.fsName + "/typsnitt_config.json");
    if (!jsonFil.exists) return cfg;
    try {
        jsonFil.open("r");
        jsonFil.encoding = "UTF-8";
        var innehall = jsonFil.read();
        jsonFil.close();
        var m;
        m = innehall.match(/"rubrik_font"\s*:\s*"([^"]+)"/);    if (m) cfg.rubrik_font    = m[1];
        m = innehall.match(/"rubrik_style"\s*:\s*"([^"]+)"/);   if (m) cfg.rubrik_style   = m[1];
        m = innehall.match(/"brodtext_font"\s*:\s*"([^"]+)"/);  if (m) cfg.brodtext_font  = m[1];
        m = innehall.match(/"brodtext_style"\s*:\s*"([^"]+)"/); if (m) cfg.brodtext_style = m[1];
        m = innehall.match(/"storlek_troskel"\s*:\s*([\d.]+)/); if (m) cfg.storlek_troskel = parseFloat(m[1]);
    } catch(e) {}
    return cfg;
}

// OPT-IN typsnittsbyte: bara textramar med namn _font_rubrik eller
// _font_brod får bytet. Alla andra textramar behåller sina typsnitt.
function sattTypsnittOptInItems(items, cfg) {
    for (var f = 0; f < items.length; f++) {
        var obj = items[f];
        if (!(obj instanceof TextFrame)) continue;
        var objNamn = "";
        try { objNamn = obj.name || ""; } catch(e) { continue; }
        if (!objNamn) continue;

        var arRubrikFont = (objNamn.indexOf("_font_rubrik") === 0);
        var arBrodFont   = (objNamn.indexOf("_font_brod") === 0);
        if (!arRubrikFont && !arBrodFont) continue;

        try {
            if (obj.characters.length === 0) continue;
            var fontNamn = arRubrikFont ? cfg.rubrik_font  : cfg.brodtext_font;
            var fontStil = arRubrikFont ? cfg.rubrik_style : cfg.brodtext_style;
            obj.texts.everyItem().appliedFont = fontNamn;
            obj.texts.everyItem().fontStyle   = fontStil;
        } catch(e) {}
    }
}

function sattTypsnittOptIn(spread, cfg) {
    sattTypsnittOptInItems(spread.allPageItems, cfg);
}

function harledSkedeHexFranDocNamn(docName) {
    var spelDir;
    if (typeof SPELET2_ROT !== "undefined" && SPELET2_ROT) {
        spelDir = new Folder(SPELET2_ROT);
    } else {
        spelDir = File($.fileName).parent.parent;
    }
    var jsonFil = File(spelDir.fsName + "/skede_config.json");
    if (!jsonFil.exists) return null;
    var cfg = {};
    try {
        jsonFil.open("r");
        jsonFil.encoding = "UTF-8";
        var innehall = jsonFil.read();
        jsonFil.close();
        var re = /"([^"]+)"\s*:\s*"(#[0-9A-Fa-f]{6})"/g;
        var m;
        while ((m = re.exec(innehall)) !== null) {
            cfg[m[1]] = m[2];
        }
    } catch(e) { return null; }
    var lower = docName.toLowerCase();
    for (var prefix in cfg) {
        if (cfg.hasOwnProperty(prefix)) {
            if (lower.indexOf(prefix.toLowerCase()) === 0) {
                return cfg[prefix];
            }
        }
    }
    return null;
}

