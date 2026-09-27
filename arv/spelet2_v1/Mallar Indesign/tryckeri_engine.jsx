// tryckeri_engine.jsx v1
//
// Gemensam motor för tryckeri-utskrift (1 motiv per sida, 3mm utfall,
// öppna skärmärken). Anropas av tunna wrappers som sätter:
//   TARGET_W_MM, TARGET_H_MM  – kortstorlek att filtrera på
//   STORLEK_NAMN              – t.ex. "58x88" (för logg och filnamn)
//
// Flöde:
//   1. Loopa fas-mappar, för varje .indd:
//      a. Skip om PDF\Tryckbara\<basnamn>_tryckeri.pdf redan finns
//      b. Öppna .indd, leta upp första _kortram, kolla bounds mot TARGET
//      c. Om matchar: datamerge (befintlig CSV-sortering) + farglagg
//      d. Skriv layout-JSON med _kortram-bounds per spread
//      e. Exportera multi-card PDF utan utfall till temp-mapp
//      f. Stäng dokument
//   2. Anropa splitta_tryckeri.py med manifest-filen
//
// Output: PDF\Tryckbara\<basnamn>_tryckeri.pdf (1 motiv per sida,
// alternerande bild/text, 3mm utfall, öppna skärmärken)

if (typeof TARGET_W_MM === "undefined") {
    alert("tryckeri_engine.jsx: TARGET_W_MM måste sättas av wrapper-skriptet.");
    exit();
}
if (typeof TARGET_H_MM === "undefined") {
    alert("tryckeri_engine.jsx: TARGET_H_MM måste sättas av wrapper-skriptet.");
    exit();
}
if (typeof STORLEK_NAMN === "undefined") {
    STORLEK_NAMN = TARGET_W_MM + "x" + TARGET_H_MM;
}

// Tolerans vid storleksjämförelse (mm). InDesign-mått kan ha små rundnings-
// fel + kortramen ritas inte alltid på exakta heltal.
var STORLEK_TOLERANS_MM = 1.5;

var ROT = "C:\\Users\\niklas.sviden\\OneDrive - Åke Sundvalls Byggnads AB\\SPELET 2\\";

var MAPPAR = {
    "L_":  ROT + "0. Ledning\\",
    "PU_": ROT + "1. Projektutveckling\\",
    "PL_": ROT + "2. Planering\\",
    "GF_": ROT + "3. Genomförande\\",
    "F_":  ROT + "4. Förvaltning\\"
};

var TRYCK_MAPP    = ROT + "PDF\\Tryckbara\\";
var TEMP_MAPP     = TRYCK_MAPP + "_tryckeri_temp\\";
var PYTHON_SKRIPT = ROT + "Mallar Indesign\\splitta_tryckeri.py";
var UTSKRIFT_JSON = ROT + "utskrift_config.json";

// Säkerställ output-mappar
var tryckMappObj = new Folder(TRYCK_MAPP);
if (!tryckMappObj.exists) tryckMappObj.create();
var tempMappObj = new Folder(TEMP_MAPP);
if (!tempMappObj.exists) tempMappObj.create();

var lyckades     = [];
var hoppadeFelStorlek = [];
var hoppadeKlara = [];
var hoppadeIngen = [];
var misslyckades = [];
var manifestPoster = [];

var loggFilSokv = ROT + "loggar\\tryckeri_" + STORLEK_NAMN + "_logg.txt";
var loggMapp = new Folder(ROT + "loggar");
if (!loggMapp.exists) loggMapp.create();
var logg = [];
function flushLogg() {
    try {
        var f = new File(loggFilSokv);
        f.open("w");
        f.encoding = "UTF-8";
        f.write(logg.join("\n"));
        f.close();
    } catch(e) {}
}
function tidsstampel() {
    var d = new Date();
    var pad = function(n) { return n < 10 ? "0" + n : "" + n; };
    return pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
}
function log(rad) {
    if (rad === "" || rad.charAt(0) === "\n" || rad.indexOf("===") === 0) {
        logg.push(rad);
    } else {
        logg.push(tidsstampel() + "  " + rad);
    }
    flushLogg();
}

log("=== Tryckeri-export " + STORLEK_NAMN + " ===");
log("Start: " + new Date().toString());
log("Mål-storlek: " + TARGET_W_MM + " × " + TARGET_H_MM + " mm (tolerans ±" + STORLEK_TOLERANS_MM + " mm)");

var MM_TO_PT = 72.0 / 25.4;

// ── Läs utskrift_config.json (för antal exemplar per fil) ────────────────
function lasUtskriftConfig() {
    var cfg = {};
    var f = new File(UTSKRIFT_JSON);
    if (!f.exists) return cfg;
    try {
        f.open("r");
        f.encoding = "UTF-8";
        var text = f.read();
        f.close();
        var re = /"([^"]+)"\s*:\s*(\d+)/g;
        var m;
        while ((m = re.exec(text)) !== null) {
            cfg[m[1]] = parseInt(m[2], 10);
        }
    } catch(e) {}
    return cfg;
}

function hamtaExemplar(cfg, basnamn) {
    if (cfg.hasOwnProperty(basnamn)) return cfg[basnamn];
    var lowNamn = basnamn.toLowerCase();
    for (var key in cfg) {
        if (key.toLowerCase() === lowNamn) return cfg[key];
    }
    var utan = basnamn.replace(/_bildsida$/i, "").replace(/_textsida$/i, "");
    var lowUtan = utan.toLowerCase();
    for (var key in cfg) {
        var keyUtan = key.toLowerCase().replace(/_bildsida$/, "").replace(/_textsida$/, "");
        if (keyUtan === lowUtan) return cfg[key];
    }
    return 1;
}

// ── Skriv "S<nr>" i alla _exemplar_*-textframes (ej _exemplar_spelare) ──
function skrivExemplarNr(mergeDoc, nr) {
    var skrivet = 0;
    var text = "S" + nr;
    for (var s = 0; s < mergeDoc.spreads.length; s++) {
        var items = mergeDoc.spreads[s].allPageItems;
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            var namn = "";
            try { namn = it.name || ""; } catch(e) { continue; }
            if (namn.indexOf("_exemplar_") !== 0) continue;
            if (namn === "_exemplar_spelare") continue;
            try {
                if (it instanceof TextFrame) {
                    it.contents = text;
                    skrivet++;
                } else if (it.textFrames && it.textFrames.length > 0) {
                    it.textFrames.firstItem().contents = text;
                    skrivet++;
                }
            } catch(e) {}
        }
    }
    return skrivet;
}

// ── Läs dokumentets sidstorlek (mallens sidstorlek = kortets storlek) ────
// Mallarna är enkla 58×88 / 88×88 / 88×146 mm-sidor; datamerge skapar en
// sida per record. Vi filtrerar alltså på documentPreferences.pageWidth.
function lasSidaStorlek(doc) {
    try {
        var p = doc.documentPreferences;
        return {
            w: p.pageWidth  / MM_TO_PT,
            h: p.pageHeight / MM_TO_PT
        };
    } catch(e) {
        return null;
    }
}

function storlekMatchar(faktisk, mal_w, mal_h, tolerans) {
    if (!faktisk) return false;
    var w_diff = Math.abs(faktisk.w - mal_w);
    var h_diff = Math.abs(faktisk.h - mal_h);
    return w_diff <= tolerans && h_diff <= tolerans;
}

// Bestäm "bild" / "text" / "okänd" baserat på filnamnet. Använder indexOf
// för att vara robust mot eventuella ExtendScript-regex-egenheter.
function detekteraSidaTyp(namn) {
    var lo = String(namn || "").toLowerCase();
    if (lo.indexOf("_bildsida") !== -1) return "bild";
    if (lo.indexOf("_textsida") !== -1) return "text";
    return "okänd";
}

// ── Hitta matchande CSV ──────────────────────────────────────────────────
function normalizeNamn(s) {
    s = s.replace(/_bildsida$/i, "").replace(/_textsida$/i, "");
    s = s.replace(/^([A-Za-z]+)_[0-9]+_/i, "$1_");
    return s.toLowerCase();
}

function hittaCSV(mapp, basnamn) {
    var f = new File(mapp.fsName + "\\" + basnamn + ".csv");
    if (f.exists) return f;
    var utan = basnamn.replace(/_bildsida$/i, "").replace(/_textsida$/i, "");
    f = new File(mapp.fsName + "\\" + utan + ".csv");
    if (f.exists) return f;
    var alla = mapp.getFiles("*.csv");
    var inddNorm = normalizeNamn(basnamn);
    for (var i = 0; i < alla.length; i++) {
        var cn = decodeURIComponent(alla[i].name).replace(/\.csv$/i, "");
        if (/_bildsida$/i.test(cn) || /_textsida$/i.test(cn)) continue;
        if (normalizeNamn(cn) === inddNorm) return alla[i];
    }
    return null;
}

// ── CSV-läsning + sortering (samma logik som master_kortproduktion) ──────
function splitCSVLine(line, delim) {
    var fields = [];
    var i = 0, n = line.length;
    while (i <= n) {
        var field = "";
        if (i < n && line.charAt(i) === '"') {
            i++;
            while (i < n) {
                var c = line.charAt(i);
                if (c === '"') {
                    if (i + 1 < n && line.charAt(i + 1) === '"') { field += '"'; i += 2; }
                    else { i++; break; }
                } else { field += c; i++; }
            }
            while (i < n && line.charAt(i) !== delim) i++;
        } else {
            while (i < n && line.charAt(i) !== delim) { field += line.charAt(i); i++; }
        }
        fields.push(field);
        if (i < n && line.charAt(i) === delim) i++; else break;
    }
    return fields;
}

function lasCSV(fil) {
    fil.open("r");
    fil.encoding = "CP1252";
    var innehall = fil.read();
    fil.close();
    if (!innehall) return [];
    var rader = innehall.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
    var avg = "\t";
    if ((rader[0] || "").indexOf("\t") === -1) {
        avg = (rader[0] || "").indexOf(";") !== -1 ? ";" : ",";
    }
    var resultat = [];
    for (var i = 0; i < rader.length; i++) {
        if (rader[i].replace(/\s/g, "") === "") continue;
        resultat.push({ rad: splitCSVLine(rader[i], avg), avg: avg });
    }
    return resultat;
}

function csvEscape(varde, delim) {
    if (varde === null || typeof varde === "undefined") return "";
    var s = String(varde);
    if (s.indexOf(delim) === -1 && s.indexOf('"') === -1 &&
        s.indexOf("\n") === -1 && s.indexOf("\r") === -1) return s;
    return '"' + s.replace(/"/g, '""') + '"';
}

function skrivCSV(fil, rader) {
    fil.open("w");
    fil.encoding = "CP1252";
    var avg = rader.length > 0 ? rader[0].avg : ";";
    for (var i = 0; i < rader.length; i++) {
        var rad = rader[i].rad;
        var escaped = [];
        for (var j = 0; j < rad.length; j++) escaped.push(csvEscape(rad[j], avg));
        fil.writeln(escaped.join(avg));
    }
    fil.close();
}

function skapaTemp(csvFil, sortKolumn, tempSokv) {
    var rader = lasCSV(csvFil);
    if (rader.length < 2) return null;
    var header = rader[0];
    var dataRader = rader.slice(1);
    var kolIdx = -1;
    if (sortKolumn) {
        for (var i = 0; i < header.rad.length; i++) {
            if (header.rad[i].replace(/^﻿/, "").replace(/\s/g, "").toLowerCase() === sortKolumn.toLowerCase()) {
                kolIdx = i; break;
            }
        }
        if (kolIdx !== -1) {
            dataRader.sort(function(a, b) {
                return parseInt(a.rad[kolIdx] || "0", 10) - parseInt(b.rad[kolIdx] || "0", 10);
            });
        }
    }
    var sorterad = [header].concat(dataRader);
    var tempFil = new File(tempSokv);
    skrivCSV(tempFil, sorterad);
    return tempFil;
}

// ── Centrera innehåll på sidan om det hamnat utanför ────────────────────
// Vissa mallar (t.ex. textsida-mallar designade för flera-poster-layout)
// har innehåll positionerat utanför 58×88-arean. När merge körs i
// "en post per sida"-läge bevaras dessa positioner — så vi får synligt
// innehåll bara på en kant av sidan. Denna funktion detekterar det och
// shiftar allt innehåll så att dess bounding-box hamnar centrerat på sidan.
function centreraInnehallPaSida(mergeDoc) {
    var auto = {
        "_fillcolor": true, "_linecolor": true, "_skede_color": true,
        "_bakgrund_color": true, "_typ": true, "_niv": true,
        "_beror_av": true, "_mildring_roll": true, "_kortram": true
    };
    var totalShift = 0;
    var spreads = mergeDoc.spreads;
    for (var s = 0; s < spreads.length; s++) {
        var spread = spreads[s];
        var sida   = spread.pages[0];
        var sb = sida.bounds; // [y1, x1, y2, x2]
        var sx1 = sb[1], sy1 = sb[0], sx2 = sb[3], sy2 = sb[2];
        var pageW = sx2 - sx1, pageH = sy2 - sy1;

        // Hitta bbox av allt synligt INNEHÅLL (ignorera automatiseringsramar
        // och små inkonsekventa ramar som ligger på pasteboard)
        var items = spread.allPageItems;
        var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        var counted = 0;
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            var namn = "";
            try { namn = it.name || ""; } catch(e) {}
            if (auto[namn]) continue;
            var b;
            try { b = it.geometricBounds; } catch(e) { continue; }
            // Skippa textframes som bara innehåller automatiseringsdata
            // (deras innehåll ser ut som "#XXXXXX" eller liknande)
            if (it instanceof TextFrame) {
                var t = "";
                try { t = (it.contents || "").replace(/\s/g, ""); } catch(e) {}
                if (/^#?[0-9A-Fa-f]{6}$/.test(t)) continue;
            }
            if (b[1] < minX) minX = b[1];
            if (b[0] < minY) minY = b[0];
            if (b[3] > maxX) maxX = b[3];
            if (b[2] > maxY) maxY = b[2];
            counted++;
        }
        if (counted === 0 || minX === Infinity) continue;

        var contentW = maxX - minX, contentH = maxY - minY;

        // Bedöm om innehåll är "i huvudsak" inom sidan: minst 50% av
        // bbox-arean ska överlappa sidan. Annars centrera om.
        var ovX1 = Math.max(minX, sx1), ovX2 = Math.min(maxX, sx2);
        var ovY1 = Math.max(minY, sy1), ovY2 = Math.min(maxY, sy2);
        var ovW = Math.max(0, ovX2 - ovX1), ovH = Math.max(0, ovY2 - ovY1);
        var ovArea = ovW * ovH;
        var contentArea = contentW * contentH;
        if (contentArea === 0) continue;
        var fraktionInne = ovArea / contentArea;
        if (fraktionInne >= 0.95) continue; // i stort sett inne — gör inget

        // Centrera innehållets bbox över sidan
        var dx = (sx1 + (pageW - contentW) / 2) - minX;
        var dy = (sy1 + (pageH - contentH) / 2) - minY;

        for (var i = 0; i < items.length; i++) {
            try {
                items[i].move([dx, dy], CoordinateSpaces.PARENT_COORDINATES);
                totalShift++;
            } catch(e) {}
        }
    }
    return totalShift;
}

// ── Rensa automatiseringsramar (samma som master_kortproduktion) ─────────
function taBortFargkoder(mergeDoc) {
    var auto = {
        "_fillcolor": true, "_linecolor": true, "_skede_color": true,
        "_bakgrund_color": true, "_typ": true, "_niv": true,
        "_beror_av": true, "_mildring_roll": true
        // OBS: _kortram BEHÅLLS — Python behöver dem inte (vi skickar JSON)
        // men de skadar inte heller eftersom de saknar fyllning/linje
    };
    var borttagna = 0;
    for (var s = mergeDoc.spreads.length - 1; s >= 0; s--) {
        var items = mergeDoc.spreads[s].allPageItems;
        for (var ri = items.length - 1; ri >= 0; ri--) {
            if (!(items[ri] instanceof TextFrame)) continue;
            if (auto[items[ri].name]) { items[ri].remove(); borttagna++; }
        }
    }
    return borttagna;
}

// ── Samla layout: varje sida = ett kort som täcker hela sidan ────────────
// Mallarna är single-card-per-page (page = card size). Datamerge skapar
// en ny sida per record. Layout-JSON struktur per sida:
//   { "page": N, "page_w_mm":.., "page_h_mm":..,
//     "cards": [{"x_mm":0, "y_mm":0, "w_mm":page_w, "h_mm":page_h}] }
function samlaKortramBounds(mergeDoc) {
    var resultat = [];
    for (var s = 0; s < mergeDoc.spreads.length; s++) {
        var spread = mergeDoc.spreads[s];
        var sida   = spread.pages[0];
        var sidaBounds = sida.bounds; // [y1, x1, y2, x2]
        var page_w_mm = (sidaBounds[3] - sidaBounds[1]) / MM_TO_PT;
        var page_h_mm = (sidaBounds[2] - sidaBounds[0]) / MM_TO_PT;

        resultat.push({
            page: s + 1,
            page_w_mm: page_w_mm,
            page_h_mm: page_h_mm,
            cards: [{
                x_mm: 0,
                y_mm: 0,
                w_mm: page_w_mm,
                h_mm: page_h_mm
            }]
        });
    }
    return resultat;
}

// Konvertera struktur till JSON-sträng (manuell — ExtendScript saknar JSON.stringify)
function toJSON(obj, indent) {
    var i = indent || "";
    var nl = "\n";
    if (obj === null) return "null";
    if (typeof obj === "number") return String(obj);
    if (typeof obj === "boolean") return obj ? "true" : "false";
    if (typeof obj === "string") {
        return '"' + obj.replace(/\\/g, "\\\\").replace(/"/g, '\\"')
                       .replace(/\n/g, "\\n").replace(/\r/g, "\\r")
                       .replace(/\t/g, "\\t") + '"';
    }
    if (obj instanceof Array) {
        if (obj.length === 0) return "[]";
        var parts = [];
        for (var k = 0; k < obj.length; k++) {
            parts.push(i + "  " + toJSON(obj[k], i + "  "));
        }
        return "[\n" + parts.join(",\n") + "\n" + i + "]";
    }
    if (typeof obj === "object") {
        var ps = [];
        for (var key in obj) {
            if (!obj.hasOwnProperty(key)) continue;
            ps.push(i + "  " + toJSON(key, "") + ": " + toJSON(obj[key], i + "  "));
        }
        if (ps.length === 0) return "{}";
        return "{\n" + ps.join(",\n") + "\n" + i + "}";
    }
    return "null";
}

function skrivJSON(sokv, data) {
    var f = new File(sokv);
    f.open("w");
    f.encoding = "UTF-8";
    f.write(toJSON(data, ""));
    f.close();
}

// ── HUVUDLOOP ────────────────────────────────────────────────────────────
var origInteraction  = app.scriptPreferences.userInteractionLevel;
var origMeasurement  = app.scriptPreferences.measurementUnit;
app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;
// Tvinga POINTS som mätenhet — annars returnerar pageWidth/geometricBounds
// värden i dokumentets unit (t.ex. mm) och vår "/MM_TO_PT"-division blir fel.
app.scriptPreferences.measurementUnit = MeasurementUnits.POINTS;
app.linkingPreferences.checkLinksAtOpen = false;

// Läs utskrift_config en gång (antal exemplar per fil)
var utskriftCfg = lasUtskriftConfig();

var fargSkript = new File(new File($.fileName).parent + "/farglagg_projektkort.jsx");

for (var prefix in MAPPAR) {
    var mapp = new Folder(MAPPAR[prefix]);
    if (!mapp.exists) continue;

    var filer = mapp.getFiles(prefix + "*.indd");

    for (var f = 0; f < filer.length; f++) {
        var inddFil = filer[f];
        var basnamn = decodeURIComponent(inddFil.name.replace(/\.indd$/i, ""));

        // ── Inkrementell: hoppa över om parad final-PDF redan finns ────────
        // basnamn = "PU_projekt_bildsida" → stem = "PU_projekt".
        // Final PDF: "<stem>_tryckeri.pdf" om 1 exemplar, annars
        //            "<stem>_S1_tryckeri.pdf" .. "<stem>_S<N>_tryckeri.pdf"
        var stem = basnamn.replace(/_bildsida$/i, "").replace(/_textsida$/i, "");
        var antalExemplar = hamtaExemplar(utskriftCfg, basnamn);

        // Hoppa över om ALLA förväntade final-PDF:er redan finns
        var allaFinns = true;
        if (antalExemplar <= 1) {
            allaFinns = (new File(TRYCK_MAPP + stem + "_tryckeri.pdf")).exists;
        } else {
            for (var ei = 1; ei <= antalExemplar; ei++) {
                if (!(new File(TRYCK_MAPP + stem + "_S" + ei + "_tryckeri.pdf")).exists) {
                    allaFinns = false; break;
                }
            }
        }
        if (allaFinns) {
            hoppadeKlara.push(basnamn);
            continue;
        }

        // Tryckeri-läge: BÅDA bildsida och textsida sorteras forward
        // (ordning_bild) så att kort #N på bildsidan matchar kort #N på
        // textsidan. Python interfolierar 1:1 vid samma position.
        // (Skiljer sig från _kombinerad-flödet där textsida är reverserad
        // för dubbelsidig utskrift på A4.)
        var sortKolumn = "ordning_bild";

        var csvFil = hittaCSV(mapp, basnamn);
        if (!csvFil) {
            hoppadeIngen.push(basnamn + " (CSV saknas)");
            continue;
        }

        log("\n--- " + basnamn + " ---");
        var filStart = new Date();
        var tempCSVSokv = mapp.fsName + "\\" + basnamn + "_~tryckeri_temp.csv";
        var tempCSV = skapaTemp(csvFil, sortKolumn, tempCSVSokv);
        var aktivCSV = tempCSV || csvFil;

        var doc = null, mergeDoc = null;
        try {
            doc = app.open(inddFil, false);

            // ── Storleksfilter (på dokumentets sidstorlek = kortets storlek) ─
            var storlek = lasSidaStorlek(doc);
            if (!storlek) {
                hoppadeIngen.push(basnamn + " (kunde inte läsa sidstorlek)");
                log("  HOPPAR: kunde inte läsa sidstorlek");
                doc.close(SaveOptions.NO);
                if (tempCSV) try { tempCSV.remove(); } catch(e) {}
                continue;
            }
            if (!storlekMatchar(storlek, TARGET_W_MM, TARGET_H_MM, STORLEK_TOLERANS_MM)) {
                hoppadeFelStorlek.push(basnamn + " (" + storlek.w.toFixed(1) +
                                       "×" + storlek.h.toFixed(1) + " mm)");
                log("  HOPPAR: sidstorlek " + storlek.w.toFixed(1) + "×" +
                    storlek.h.toFixed(1) + " ≠ mål " + TARGET_W_MM + "×" + TARGET_H_MM);
                doc.close(SaveOptions.NO);
                if (tempCSV) try { tempCSV.remove(); } catch(e) {}
                continue;
            }
            log("  Sidstorlek matchar: " + storlek.w.toFixed(1) + "×" + storlek.h.toFixed(1) + " mm");

            // ── Uppdatera länkar ───────────────────────────────────────────
            for (var li = 0; li < doc.links.length; li++) {
                var lnk = doc.links[li];
                if (lnk.status === LinkStatus.LINK_OUT_OF_DATE) {
                    try { lnk.update(); } catch(ue) {}
                }
            }

            // ── Datamerge ──────────────────────────────────────────────────
            try { doc.dataMergeProperties.removeDataSource(); } catch(e) {}
            doc.dataMergeProperties.selectDataSource(aktivCSV);

            // Tvinga "En post per dokumentsida" — annars placerar InDesign
            // multipla poster per sida enligt mallens layout, vilket gör att
            // innehållet hamnar utanför 58×88 (eftersom det inte får plats).
            // recordsPerDocumentPage=1 motsvarar UI-valet "En post".
            try {
                var dmo = doc.dataMergeProperties.dataMergeOption;
                var sattVarden = [];
                // Sätt recordsPerDocumentPage=1 (en post per sida)
                try { dmo.recordsPerDocumentPage = 1; sattVarden.push("recordsPerDocumentPage=1"); } catch(e1) {}
                // Om InDesign har en separat boolean för multi-record:
                try { dmo.placeAllRecordsOnSinglePage = false; sattVarden.push("placeAllRecordsOnSinglePage=false"); } catch(e2) {}
                // Vissa InDesign-versioner: dataMergePreferences.recordsPerPage
                try {
                    var prefs = app.dataMergePreferences || doc.dataMergePreferences;
                    if (prefs) {
                        try { prefs.recordsPerDocumentPage = 1; sattVarden.push("prefs.recordsPerDocumentPage=1"); } catch(e3) {}
                    }
                } catch(e4) {}
                log("  Datamerge-läge: " + (sattVarden.length > 0
                    ? sattVarden.join(", ")
                    : "kunde inte sättas — använder default"));
            } catch(e) {
                log("  VARNING: kunde inte sätta merge-läge: " + e.message);
            }

            doc.dataMergeProperties.mergeRecords();
            mergeDoc = app.activeDocument;
            log("  Merge klar: " + mergeDoc.spreads.length + " spreads");

            // ── Färgläggning ───────────────────────────────────────────────
            if (fargSkript.exists) {
                TYST = true;
                SPELET2_ROT = ROT;
                EXEMPLAR_NR = null;
                app.doScript(fargSkript, ScriptLanguage.JAVASCRIPT, undefined,
                             UndoModes.ENTIRE_SCRIPT, "Färglägg");
                mergeDoc = app.activeDocument;
                log("  Färgläggning klar");
            }

            // ── Centrera innehåll om det hamnat utanför sidan ─────────────
            // Säkerhetsnät för mallar med innehåll positionerat på pasteboard
            // (vanligt med textsida-mallar designade för multi-record layout).
            try {
                var skiftade = centreraInnehallPaSida(mergeDoc);
                if (skiftade > 0) {
                    log("  Centrerade innehåll på " + skiftade + " items (innehåll var utanför sidan)");
                }
            } catch(cee) {
                log("  VARNING: kunde inte centrera innehåll: " + cee.message);
            }

            // ── Samla kortram-bounds till JSON (samma layout för alla exemplar) ─
            var layout = samlaKortramBounds(mergeDoc);

            // ── Rensa automatiseringsramar (men EJ _exemplar_-frames!) ───────
            var borttagna = taBortFargkoder(mergeDoc);
            log("  Tog bort " + borttagna + " automatiseringsramar");

            // ── Räkna _exemplar_-frames (returnerar 0 om inga finns) ────────
            var antalFrames = skrivExemplarNr(mergeDoc, 1);
            if (antalExemplar > 1 && antalFrames === 0) {
                log("  VARNING: " + antalExemplar + " exemplar konfigurerat men inga " +
                    "_exemplar_-frames hittades. Exporterar 1 PDF, kopierar " +
                    (antalExemplar - 1) + " gånger.");
            }
            log("  Exemplar: " + antalExemplar +
                (antalFrames > 0 ? " (med S-numrering, " + antalFrames + " frames)"
                                 : " (kopior eller enkel export)"));

            // ── PDF-export-prefs (gemensamma för alla exemplar) ─────────────
            var prefs = app.pdfExportPreferences;
            var save = {
                cropMarks: prefs.cropMarks, bleedMarks: prefs.bleedMarks,
                regMarks: prefs.registrationMarks, pageInfo: prefs.pageInformationMarks,
                colorBars: prefs.colorBars, useDocBleed: prefs.useDocumentBleedWithPDF,
                bT: prefs.bleedTop, bB: prefs.bleedBottom,
                bI: prefs.bleedInside, bO: prefs.bleedOutside
            };
            prefs.cropMarks = false; prefs.bleedMarks = false;
            prefs.registrationMarks = false; prefs.pageInformationMarks = false;
            prefs.colorBars = false; prefs.useDocumentBleedWithPDF = false;
            prefs.bleedTop = "0mm"; prefs.bleedBottom = "0mm";
            prefs.bleedInside = "0mm"; prefs.bleedOutside = "0mm";

            try {
                if (antalExemplar > 1 && antalFrames > 0) {
                    // ── Loopa exemplar 1..N: skriv S<nr>, exportera + JSON per nr ──
                    for (var nr = 1; nr <= antalExemplar; nr++) {
                        if (nr > 1) skrivExemplarNr(mergeDoc, nr);
                        var suffix       = "_S" + nr;
                        var tempPDFSokvN = TEMP_MAPP + basnamn + suffix + "_temp.pdf";
                        var jsonSokvN    = TEMP_MAPP + basnamn + suffix + "_layout.json";
                        skrivJSON(jsonSokvN, {
                            basnamn: basnamn,
                            storlek_namn: STORLEK_NAMN,
                            card_w_mm: TARGET_W_MM,
                            card_h_mm: TARGET_H_MM,
                            spreads: layout
                        });
                        mergeDoc.exportFile(ExportFormat.PDF_TYPE, new File(tempPDFSokvN), false);
                        log("  Exemplar S" + nr + ": " + tempPDFSokvN);
                        manifestPoster.push({
                            basnamn: basnamn,
                            stem: stem,
                            sida_typ: detekteraSidaTyp(basnamn),
                            exemplar_nr: nr,
                            temp_pdf: tempPDFSokvN,
                            layout_json: jsonSokvN,
                            final_pdf: TRYCK_MAPP + stem + "_S" + nr + "_tryckeri.pdf",
                            csv_path: csvFil.fsName,
                            fas_prefix: prefix
                        });
                    }
                } else {
                    // ── Enkel körning: en PDF, ev. kopierad N gånger ────────────
                    var tempPDFSokv = TEMP_MAPP + basnamn + "_temp.pdf";
                    var jsonSokv    = TEMP_MAPP + basnamn + "_layout.json";
                    skrivJSON(jsonSokv, {
                        basnamn: basnamn,
                        storlek_namn: STORLEK_NAMN,
                        card_w_mm: TARGET_W_MM,
                        card_h_mm: TARGET_H_MM,
                        spreads: layout
                    });
                    mergeDoc.exportFile(ExportFormat.PDF_TYPE, new File(tempPDFSokv), false);
                    log("  Temp-PDF: " + tempPDFSokv);

                    if (antalExemplar > 1) {
                        // Inga _exemplar_-frames men >1 exemplar: producera identiska kopior
                        for (var nr = 1; nr <= antalExemplar; nr++) {
                            manifestPoster.push({
                                basnamn: basnamn,
                                stem: stem,
                                sida_typ: detekteraSidaTyp(basnamn),
                                exemplar_nr: nr,
                                temp_pdf: tempPDFSokv,
                                layout_json: jsonSokv,
                                final_pdf: TRYCK_MAPP + stem + "_S" + nr + "_tryckeri.pdf",
                                csv_path: csvFil.fsName,
                                fas_prefix: prefix
                            });
                        }
                    } else {
                        manifestPoster.push({
                            basnamn: basnamn,
                            stem: stem,
                            sida_typ: detekteraSidaTyp(basnamn),
                            exemplar_nr: 1,
                            temp_pdf: tempPDFSokv,
                            layout_json: jsonSokv,
                            final_pdf: TRYCK_MAPP + stem + "_tryckeri.pdf",
                            csv_path: csvFil.fsName,
                            fas_prefix: prefix
                        });
                    }
                }
            } finally {
                prefs.cropMarks = save.cropMarks; prefs.bleedMarks = save.bleedMarks;
                prefs.registrationMarks = save.regMarks;
                prefs.pageInformationMarks = save.pageInfo;
                prefs.colorBars = save.colorBars;
                prefs.useDocumentBleedWithPDF = save.useDocBleed;
                try { prefs.bleedTop = save.bT; prefs.bleedBottom = save.bB;
                      prefs.bleedInside = save.bI; prefs.bleedOutside = save.bO; } catch(e) {}
            }

            try { mergeDoc.close(SaveOptions.NO); } catch(e) {}
            try { doc.close(SaveOptions.NO); } catch(e) {}

            var sek = Math.round((new Date() - filStart) / 1000);
            lyckades.push(basnamn + " (" + sek + "s)");
            log("  OK (" + sek + "s)");
            try { $.gc(); } catch(e) {}
        } catch(e) {
            misslyckades.push(basnamn + ": " + e.message);
            log("  FEL: " + e.message);
            try { if (mergeDoc) mergeDoc.close(SaveOptions.NO); } catch(e2) {}
            try { if (doc) doc.close(SaveOptions.NO); } catch(e3) {}
        }

        if (tempCSV) { try { tempCSV.remove(); } catch(e) {} }
    }
}

app.linkingPreferences.checkLinksAtOpen = true;
app.scriptPreferences.userInteractionLevel = origInteraction;
app.scriptPreferences.measurementUnit      = origMeasurement;

// ── Skriv manifest ───────────────────────────────────────────────────────
var manifestSokv = TEMP_MAPP + "manifest_" + STORLEK_NAMN + ".json";
skrivJSON(manifestSokv, {
    storlek_namn: STORLEK_NAMN,
    card_w_mm: TARGET_W_MM,
    card_h_mm: TARGET_H_MM,
    rot: ROT,
    tryck_mapp: TRYCK_MAPP,
    poster: manifestPoster
});
log("\nManifest: " + manifestSokv + " (" + manifestPoster.length + " poster)");

// ── Anropa Python ────────────────────────────────────────────────────────
// Strategi: skriv en .bat-fil med python-anropet och kör den synkront via
// VBScript (samma mönster som master_kortproduktion.jsx använder för
// excel_till_config.bat).
function korPython(skriptSokv, manifestSokv) {
    var pyOut   = TEMP_MAPP + "splitta_log_" + STORLEK_NAMN + ".txt";
    var pyErr   = TEMP_MAPP + "splitta_err_" + STORLEK_NAMN + ".txt";
    var batSokv = TEMP_MAPP + "_run_splitta_" + STORLEK_NAMN + ".bat";

    var batFil = new File(batSokv);
    batFil.open("w");
    batFil.encoding = "UTF-8";
    batFil.writeln("@echo off");
    batFil.writeln("chcp 65001 >nul");
    batFil.writeln('python "' + skriptSokv + '" "' + manifestSokv +
                   '" > "' + pyOut + '" 2> "' + pyErr + '"');
    batFil.writeln('exit /b %ERRORLEVEL%');
    batFil.close();

    var vbs = 'Set sh = CreateObject("WScript.Shell")\n' +
              'sh.Run Chr(34) & "' + batSokv + '" & Chr(34), 0, True\n';
    try {
        app.doScript(vbs, ScriptLanguage.VISUAL_BASIC);
        return { ok: true, log: pyOut, err: pyErr, bat: batSokv };
    } catch(e) {
        return { ok: false, msg: e.message };
    }
}

if (manifestPoster.length > 0) {
    var pythonFil = new File(PYTHON_SKRIPT);
    if (!pythonFil.exists) {
        log("FEL: " + PYTHON_SKRIPT + " saknas");
    } else {
        log("\nKör splitta_tryckeri.py...");
        var pyRes = korPython(PYTHON_SKRIPT, manifestSokv);
        if (pyRes.ok) {
            log("  Python klar. Logg: " + pyRes.log);
        } else {
            log("  FEL: " + pyRes.msg);
        }
    }
} else {
    log("\nInga filer att processa — hoppar Python");
}

log("\nSlut: " + new Date().toString());
flushLogg();

// ── Slutrapport ──────────────────────────────────────────────────────────
var rapport = "=== KLART (" + STORLEK_NAMN + ") ===\n\n";
rapport += "Lyckades: " + lyckades.length + "\n";
for (var i = 0; i < lyckades.length; i++) rapport += "  ✓ " + lyckades[i] + "\n";

if (hoppadeKlara.length > 0) {
    rapport += "\nHoppade (PDF finns redan): " + hoppadeKlara.length + "\n";
    for (var i = 0; i < hoppadeKlara.length; i++) rapport += "  – " + hoppadeKlara[i] + "\n";
}
if (hoppadeFelStorlek.length > 0) {
    rapport += "\nHoppade (annan storlek än " + STORLEK_NAMN + "): " + hoppadeFelStorlek.length + "\n";
    // Lista bara de första 10 för att inte spamma alert-rutan
    var visa = Math.min(hoppadeFelStorlek.length, 10);
    for (var i = 0; i < visa; i++) rapport += "  – " + hoppadeFelStorlek[i] + "\n";
    if (hoppadeFelStorlek.length > 10) rapport += "  ... (+" + (hoppadeFelStorlek.length - 10) + " till)\n";
}
if (hoppadeIngen.length > 0) {
    rapport += "\nHoppade (saknar data): " + hoppadeIngen.length + "\n";
    for (var i = 0; i < hoppadeIngen.length; i++) rapport += "  – " + hoppadeIngen[i] + "\n";
}
if (misslyckades.length > 0) {
    rapport += "\nFel: " + misslyckades.length + "\n";
    for (var i = 0; i < misslyckades.length; i++) rapport += "  ✗ " + misslyckades[i] + "\n";
}
rapport += "\nOutput: " + TRYCK_MAPP + "*_tryckeri.pdf";
rapport += "\nLogg: " + loggFilSokv;
alert(rapport);

