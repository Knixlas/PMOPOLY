// master_kortproduktion.jsx v17
// Nytt i v17:
//   - TRYCK_MODE-stöd: master_tryckbart.jsx kan sätta global TRYCK_MODE=true
//     för att byta output till PDF\Tryckbara\ + suffix _tryck, lägga till
//     utfall + skärmärken (via onTryckPrep callback) och sätta bleed i
//     PDF-export.
// v16: Prestandafix — farglagg körs EN gång/fil, skrivExemplarNr separat.
//   - UndoModes.FAST_ENTIRE_SCRIPT istället för ENTIRE_SCRIPT (snabbare).
//   - rensaGamlaPDFer() tar bort stale PDF:er innan export.
// v15: När exemplar > 1 exporteras N separata PDF:er (_1, _2, ...).
// v14: Kör excel_till_config.bat SYNKRONT som första steg.
//   Varnar i slutrapporten när indd-filer saknar post i configfilen.
// v13: Exporterar ALLTID bara EN PDF per indd-fil.
//   Antal exemplar skrivs till PDF\exemplar_map.json så interfoliera-steget
//   kan kopiera filen rätt antal gånger vid MASTER-byggandet.
// v12: CSV-sortering via kolumnerna ordning_bild / ordning_text.
// v10: interfoliera_pdf.py efter export.
// v9:  tar bort _fillcolor/_linecolor-textramar.
// v8:  läser utskrift_config.json för antal exemplar.

// TRYCK_MODE: sätts till true av master_tryckbart.jsx (wrapper)
// för att aktivera utfall, skärmärken och export till Tryckbara/.
if (typeof TRYCK_MODE === "undefined") TRYCK_MODE = false;

// DEBUG_ENDAST_FIL: om satt (sträng), skippas alla INDD-filer vars basnamn
// INTE innehåller denna sträng. Används för snabb felsökning — kör bara
// EN fil istället för hela 44-filers marathon.
// Exempel: DEBUG_ENDAST_FIL = "PU_personal"  → kör bara PU_personal_bildsida + _textsida
if (typeof DEBUG_ENDAST_FIL === "undefined") DEBUG_ENDAST_FIL = "";

var ROT = "C:\\Users\\niklas.sviden\\OneDrive - Åke Sundvalls Byggnads AB\\SPELET 2\\";

var MAPPAR = {
    "L_":  ROT + "0. Ledning\\",
    "PU_": ROT + "1. Projektutveckling\\",
    "PL_": ROT + "2. Planering\\",
    "GF_": ROT + "3. Genomförande\\",
    "F_":  ROT + "4. Förvaltning\\",
};

var PDF_MAPP      = ROT + (TRYCK_MODE ? "PDF\\Tryckbara\\" : "PDF\\");
var TRYCK_SUFFIX  = TRYCK_MODE ? "_tryck" : "";

var pdfFolder = new Folder(PDF_MAPP);
if (!pdfFolder.exists) pdfFolder.create();

var skriptFil       = new File($.fileName);
var fargSkript      = new File(skriptFil.parent + "/farglagg_projektkort.jsx");
var utskriftJson    = new File(ROT + "utskrift_config.json");
var excelBat        = new File(ROT + "excel_till_config.bat");
var exemplarMapFil  = new File(PDF_MAPP + "exemplar_map.json");

var lyckades      = [];
var misslyckades  = [];
var hoppades      = [];
var logg          = [];
var exemplarMap   = {};  // { "GF_garantibesiktning_bildsida": 4, ... }
var fallbackNamn  = [];  // Indd-filer utan post i configfilen (varning)

// Skriv inkrementellt till loggfilen så vi ser exakt var skriptet hängde
// om det kraschar/fryser i mitten av körningen.
var loggFilSokv = null;  // sätts när ROT är läst
function flushLogg() {
    if (!loggFilSokv) return;
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
    // Tomma rader + sektionsdelare loggas utan tidsstämpel (snyggare)
    if (rad === "" || rad.charAt(0) === "\n" || rad.indexOf("===") === 0) {
        logg.push(rad);
    } else {
        logg.push(tidsstampel() + "  " + rad);
    }
    flushLogg();
}

// ── Kör excel_till_config.bat SYNKRONT via VBScript ───────────────────────
// .execute() är asynkron, vi behöver vänta på att Python-scriptet skrivit
// klart utskrift_config.json INNAN vi läser den.
function körExcelKonvertering() {
    if (!excelBat.exists) {
        log("OBS: excel_till_config.bat saknas – använder befintlig utskrift_config.json");
        return false;
    }

    log("Kör excel_till_config.bat (synkront)...");

    // Bygg VBScript: WScript.Shell.Run (cmd, intWindowStyle=0 dold, bWaitOnReturn=True)
    var vbs = 'Set sh = CreateObject("WScript.Shell")\n' +
              'sh.Run Chr(34) & "' + excelBat.fsName + '" & Chr(34), 0, True\n';

    try {
        app.doScript(vbs, ScriptLanguage.VISUAL_BASIC);
        log("  excel_till_config.bat klar");
        return true;
    } catch(e) {
        log("  VARNING: Kunde inte köra excel_till_config.bat: " + e.message);
        log("  Fortsätter med befintlig utskrift_config.json");
        return false;
    }
}

// ── Kör interfoliering via .bat (öppnas i eget fönster) ──────────────────
function körInterfoliering() {
    var bat = new File(ROT + "interfoliera.bat");
    if (bat.exists) {
        bat.execute();
        log("  Öppnade interfoliera.bat");
    } else {
        log("  OBS: interfoliera.bat saknas i SPELET 2-mappen");
    }
}

// ── Läs utskrift_config.json ─────────────────────────────────────────────
function lasUtskriftConfig() {
    var cfg = {};
    if (!utskriftJson.exists) {
        log("OBS: utskrift_config.json saknas – alla filer exporteras i 1 exemplar");
        return cfg;
    }
    try {
        utskriftJson.open("r");
        utskriftJson.encoding = "UTF-8";
        var text = utskriftJson.read();
        utskriftJson.close();
        var re = /"([^"]+)"\s*:\s*(\d+)/g;
        var m;
        while ((m = re.exec(text)) !== null) {
            cfg[m[1]] = parseInt(m[2], 10);
        }
    } catch(e) {
        log("FEL vid läsning av utskrift_config.json: " + e);
    }
    return cfg;
}

// Hämta antal exemplar + signalera om det var fallback (ingen matchning)
function hamtaExemplar(cfg, basnamn) {
    // 1. Exakt match
    if (cfg.hasOwnProperty(basnamn)) return { antal: cfg[basnamn], fallback: false };

    // 2. Case-insensitive match
    var lowNamn = basnamn.toLowerCase();
    for (var key in cfg) {
        if (key.toLowerCase() === lowNamn) return { antal: cfg[key], fallback: false };
    }

    // 3. Strippa _bildsida/_textsida och matcha igen (case-insensitive)
    var utan = basnamn.replace(/_bildsida$/i, "").replace(/_textsida$/i, "");
    var lowUtan = utan.toLowerCase();
    for (var key in cfg) {
        var lowKey = key.toLowerCase();
        var keyUtan = lowKey.replace(/_bildsida$/, "").replace(/_textsida$/, "");
        if (keyUtan === lowUtan) return { antal: cfg[key], fallback: false };
    }

    return { antal: 1, fallback: true };
}

// ── Skriv exemplar_map.json för interfoliering ────────────────────────────
function skrivExemplarMap() {
    var parts = [];
    for (var key in exemplarMap) {
        var safe = key.replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
        parts.push("  \"" + safe + "\": " + exemplarMap[key]);
    }
    var json = "{\n" + parts.join(",\n") + "\n}\n";

    exemplarMapFil.open("w");
    exemplarMapFil.encoding = "UTF-8";
    exemplarMapFil.write(json);
    exemplarMapFil.close();
    log("  Skrev exemplar_map.json (" + parts.length + " poster)");
}

// ── Hitta matchande CSV ───────────────────────────────────────────────────
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

// ── Läs CSV → array av rader ─────────────────────────────────────────────
// RFC 4180-ish parser: respekterar dubbelcitat. Ett fält som omges av "..."
// kan innehålla avgränsaren själv (t.ex. ; inuti en beskrivning) och
// dubbel-citat skrivs som "". Utan detta blir rader med ; i Beskrivnings-
// kolumnen felparsade -> fel kolumnindex för ordning_bild -> fel sortering.
function splitCSVLine(line, delim) {
    var fields = [];
    var i = 0;
    var n = line.length;
    while (i <= n) {
        var field = "";
        if (i < n && line.charAt(i) === '"') {
            i++;  // konsumera öppnande "
            while (i < n) {
                var c = line.charAt(i);
                if (c === '"') {
                    if (i + 1 < n && line.charAt(i + 1) === '"') {
                        field += '"';
                        i += 2;
                    } else {
                        i++;  // konsumera stängande "
                        break;
                    }
                } else {
                    field += c;
                    i++;
                }
            }
            // Hoppa över ev. skräp fram till nästa avgränsare
            while (i < n && line.charAt(i) !== delim) i++;
        } else {
            while (i < n && line.charAt(i) !== delim) {
                field += line.charAt(i);
                i++;
            }
        }
        fields.push(field);
        if (i < n && line.charAt(i) === delim) {
            i++;  // konsumera avgränsare och fortsätt
        } else {
            break;
        }
    }
    return fields;
}

function lasCSV(fil) {
    fil.open("r");
    fil.encoding = "CP1252";
    var innehall = fil.read();
    fil.close();

    if (!innehall || innehall.length === 0) return [];

    var rader = innehall.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");

    var forstaRad = rader[0] || "";
    var avg = "\t";
    if (forstaRad.indexOf("\t") === -1) {
        avg = forstaRad.indexOf(";") !== -1 ? ";" : ",";
    }

    var resultat = [];
    for (var i = 0; i < rader.length; i++) {
        if (rader[i].replace(/\s/g, "") === "") continue;
        resultat.push({ rad: splitCSVLine(rader[i], avg), avg: avg });
    }
    return resultat;
}

// Citera ett fältvärde om det innehåller avgränsare, citattecken eller
// radbrytning. Annars skriv som-är.
function csvEscape(varde, delim) {
    if (varde === null || typeof varde === "undefined") return "";
    var s = String(varde);
    if (s.indexOf(delim) === -1 && s.indexOf('"') === -1 &&
        s.indexOf("\n") === -1 && s.indexOf("\r") === -1) {
        return s;
    }
    return '"' + s.replace(/"/g, '""') + '"';
}

function skrivCSV(fil, rader) {
    fil.open("w");
    fil.encoding = "CP1252";
    var avg = rader.length > 0 ? rader[0].avg : ";";
    for (var i = 0; i < rader.length; i++) {
        var rad = rader[i].rad;
        var escaped = [];
        for (var j = 0; j < rad.length; j++) {
            escaped.push(csvEscape(rad[j], avg));
        }
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
                kolIdx = i;
                break;
            }
        }
        if (kolIdx !== -1) {
            dataRader.sort(function(a, b) {
                return parseInt(a.rad[kolIdx] || "0", 10) - parseInt(b.rad[kolIdx] || "0", 10);
            });
            log("  Sorterade efter '" + sortKolumn + "' (kolumn " + kolIdx + ")");
        } else {
            log("  OBS: kolumnen '" + sortKolumn + "' saknas – bara encoding-konvertering");
        }
    }

    var sorterad = [header].concat(dataRader);
    var tempFil = new File(tempSokv);
    skrivCSV(tempFil, sorterad);
    return tempFil;
}

// Rensa bort textramar som BARA finns för automatisering (inte synligt
// innehåll). Visuella element som _klass (A/B/C/D), _steg, _skede_niv\u00e5
// ("NIVÅ 3"), _exemplar_* (siffran) lämnas orörda.
function taBortFargkoder(mergeDoc) {
    var borttagna = 0;
    var automatiseringsNamn = {
        "_fillcolor":       true,
        "_linecolor":       true,
        "_skede_color":     true,
        "_bakgrund_color":  true,
        "_typ":             true,
        "_niv":             true,
        "_beror_av":        true,
        "_mildring_roll":   true,
        "_kortram":         true   // tryck-mode: trim-ram per kort
    };
    for (var s = mergeDoc.spreads.length - 1; s >= 0; s--) {
        var items = mergeDoc.spreads[s].allPageItems;
        for (var ri = items.length - 1; ri >= 0; ri--) {
            if (!(items[ri] instanceof TextFrame)) continue;
            var namn = items[ri].name;
            if (automatiseringsNamn[namn]) {
                items[ri].remove();
                borttagna++;
            }
        }
    }
    return borttagna;
}

// Rensa gamla basnamn.pdf och basnamn_N.pdf INNAN ny export. Annars kan
// interfoliera plocka upp stale PDF:er från tidigare körningar.
function rensaGamlaPDFer(pdfMapp, basnamn) {
    var folder = new Folder(pdfMapp);
    if (!folder.exists) return 0;
    var escBas = basnamn.replace(/[.+*?()\[\]^$|\\]/g, "\\$&");
    var pattern = new RegExp("^" + escBas + "(_\\d+)?\\.pdf$", "i");
    var borttagna = 0;
    var allaFiler = folder.getFiles();
    for (var i = 0; i < allaFiler.length; i++) {
        var fn = allaFiler[i] instanceof File ? allaFiler[i].name : "";
        if (pattern.test(fn)) {
            try { allaFiler[i].remove(); borttagna++; } catch(e) {}
        }
    }
    return borttagna;
}

function exporteraPDF(mergeDoc, pdfSokv) {
    if (!TRYCK_MODE) {
        mergeDoc.exportFile(ExportFormat.PDF_TYPE, new File(pdfSokv), false);
        return;
    }
    // TRYCK_MODE: sätt bleed-area runt sidan så skärmärken/utfall
    // hamnar INOM exporterade MediaBox även om de ligger utanför sidkanten.
    var prefs = app.pdfExportPreferences;
    var save = {
        cropMarks:     prefs.cropMarks,
        bleedMarks:    prefs.bleedMarks,
        regMarks:      prefs.registrationMarks,
        pageInfo:      prefs.pageInformationMarks,
        colorBars:     prefs.colorBars,
        useDocBleed:   prefs.useDocumentBleedWithPDF,
        bT: prefs.bleedTop, bB: prefs.bleedBottom,
        bI: prefs.bleedInside, bO: prefs.bleedOutside
    };
    try {
        // Vi ritar egna skärmärken — stäng av InDesigns egna
        prefs.cropMarks            = false;
        prefs.bleedMarks           = false;
        prefs.registrationMarks    = false;
        prefs.pageInformationMarks = false;
        prefs.colorBars            = false;
        prefs.useDocumentBleedWithPDF = false;
        prefs.bleedTop    = "5mm";
        prefs.bleedBottom = "5mm";
        prefs.bleedInside = "5mm";
        prefs.bleedOutside = "5mm";
        mergeDoc.exportFile(ExportFormat.PDF_TYPE, new File(pdfSokv), false);
    } finally {
        prefs.cropMarks            = save.cropMarks;
        prefs.bleedMarks           = save.bleedMarks;
        prefs.registrationMarks    = save.regMarks;
        prefs.pageInformationMarks = save.pageInfo;
        prefs.colorBars            = save.colorBars;
        prefs.useDocumentBleedWithPDF = save.useDocBleed;
        try { prefs.bleedTop    = save.bT; } catch(e) {}
        try { prefs.bleedBottom = save.bB; } catch(e) {}
        try { prefs.bleedInside = save.bI; } catch(e) {}
        try { prefs.bleedOutside = save.bO; } catch(e) {}
    }
}

// Skriv snabbt in exemplarsiffra i alla _exemplar_*-textramar.
// Används istället för att köra om farglagg_projektkort.jsx N gånger.
// Prefixas med "S" (t.ex. "S3") så bubblan visar "Steg N".
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

// ════════════════════════════════════════════════════════════════════════
// HUVUDLOOP
// ════════════════════════════════════════════════════════════════════════
// Säkerställ att loggar-mappen finns
var loggMapp = new Folder(ROT + "loggar");
if (!loggMapp.exists) loggMapp.create();
loggFilSokv = ROT + "loggar\\kortproduktion_logg.txt";
log("=== Kortproduktion v16 ===");
log("Start: " + new Date().toString());

// STEG 0: Generera utskrift_config.json från färgschema.xlsx
körExcelKonvertering();

var utskriftCfg = lasUtskriftConfig();
var cfgAntal = 0;
for (var k in utskriftCfg) cfgAntal++;
log("Läste " + cfgAntal + " poster från utskrift_config.json");

var origInteraction = app.scriptPreferences.userInteractionLevel;
app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;
app.linkingPreferences.checkLinksAtOpen = false;

for (var prefix in MAPPAR) {
    var mapp = new Folder(MAPPAR[prefix]);
    if (!mapp.exists) { log("FEL: Mapp saknas: " + MAPPAR[prefix]); continue; }

    var filer = mapp.getFiles(prefix + "*.indd");

    for (var f = 0; f < filer.length; f++) {
        var inddFil = filer[f];
        var basnamn = decodeURIComponent(inddFil.name.replace(/\.indd$/i, ""));

        // DEBUG_ENDAST_FIL: skippa filer som inte matchar felsöknings-filtret
        if (DEBUG_ENDAST_FIL && basnamn.toLowerCase().indexOf(DEBUG_ENDAST_FIL.toLowerCase()) < 0) {
            continue;
        }

        var sortKolumn = "";
        if (basnamn.match(/bildsida$/i)) {
            sortKolumn = "ordning_bild";
        } else if (basnamn.match(/textsida$/i)) {
            sortKolumn = "ordning_text";
        }

        var csvFil = hittaCSV(mapp, basnamn);
        if (!csvFil) {
            hoppades.push(basnamn);
            log("HOPPAR: " + basnamn + " (CSV saknas)");
            continue;
        }

        var res = hamtaExemplar(utskriftCfg, basnamn);
        var exemplar = res.antal;
        if (res.fallback) {
            fallbackNamn.push(basnamn);
        }

        log("\n--- " + basnamn + " (" + exemplar + " ex" +
            (res.fallback ? " – FALLBACK, inte i config!" : "") + ") ---");
        var filStart = new Date();
        log("CSV: " + csvFil.name + "  sortkolumn: " + (sortKolumn || "ingen"));

        var tempSokv = mapp.fsName + "\\" + basnamn + "_~temp.csv";
        var tempFil  = skapaTemp(csvFil, sortKolumn, tempSokv);
        var aktivCSV = tempFil || csvFil;

        try {
            log("  [öppnar .indd]");
            var doc = app.open(inddFil, false);

            log("[kollar länkar]");
            var uppdLankar = 0;
            for (var li = 0; li < doc.links.length; li++) {
                var lnk = doc.links[li];
                if (lnk.status === LinkStatus.LINK_OUT_OF_DATE) {
                    var lnkNamn = "";
                    try { lnkNamn = lnk.name || ""; } catch(ne) {}
                    log("  [uppdaterar länk: " + lnkNamn + "]");
                    try { lnk.update(); uppdLankar++; } catch(ue) {
                        log("  [FEL vid länkuppdatering: " + ue.message + "]");
                    }
                } else if (lnk.status === LinkStatus.LINK_MISSING) {
                    try { log("  [VARNING: bruten länk: " + lnk.name + "]"); } catch(me) {}
                }
            }
            if (uppdLankar > 0) log("Uppdaterade " + uppdLankar + " ändrade länk(ar)");

            log("  [data merge]");
            try { doc.dataMergeProperties.removeDataSource(); } catch(e) {}
            doc.dataMergeProperties.selectDataSource(aktivCSV);
            doc.dataMergeProperties.mergeRecords();

            var mergeDoc = app.activeDocument;
            log("  [merge klar, " + mergeDoc.spreads.length + " spreads]");

            TYST = true;
            SPELET2_ROT = ROT;
            if (fargSkript.exists) {
                log("  [kör farglagg]");
                EXEMPLAR_NR = null;
                // ENTIRE_SCRIPT (inte FAST_ENTIRE_SCRIPT) — vissa operationer
                // (bl.a. sendToBack och polygon-fyllning) beter sig inte
                // tillförlitligt under FAST_ENTIRE_SCRIPT.
                app.doScript(fargSkript, ScriptLanguage.JAVASCRIPT, undefined,
                             UndoModes.ENTIRE_SCRIPT, "Färglägg");
                mergeDoc = app.activeDocument;
                log("  [farglagg klar]");
            }

            // Tryck-läge: lägg till utfall + skärmärken per _kortram
            if (TRYCK_MODE && typeof onTryckPrep === "function") {
                log("  [tryck-prep]");
                try {
                    var tr = onTryckPrep(mergeDoc);
                    if (tr) {
                        log("  [tryck-prep klar: " + tr.kort + " kort, " +
                            tr.bleed + " utfall, " + tr.marks + " skärmärken]");
                        if (tr.logg) {
                            for (var tli = 0; tli < tr.logg.length; tli++) {
                                log("    " + tr.logg[tli]);
                            }
                        }
                    }
                } catch(tpe) {
                    log("  FEL i onTryckPrep: " + tpe.message);
                }
            }

            // Rensa gamla PDF:er (basnamn.pdf + alla basnamn_N.pdf) innan export.
            // Hindrar interfoliera från att plocka upp stale filer.
            var rensade = rensaGamlaPDFer(PDF_MAPP, basnamn + TRYCK_SUFFIX);
            if (rensade > 0) log("  Rensade " + rensade + " gamla PDF:er");

            if (exemplar > 1) {
                // Kolla om dokumentet har _exemplar_-ramar att fylla i.
                // Utan dem blir alla kopior identiska — då räcker EN export
                // och PDF:en kopieras på disk. Snabbare och undviker hängning
                // i PDF-export efter upprepade export-cykler på samma doc.
                var antalExemplar = skrivExemplarNr(mergeDoc, 1);

                if (antalExemplar === 0) {
                    log("  Inga _exemplar_-ramar — exporterar 1 PDF, kopierar " +
                        (exemplar - 1) + " gånger på disk");
                    var borttagna = taBortFargkoder(mergeDoc);
                    log("  Tog bort " + borttagna + " automatiserings-textramar");

                    var forstaNamn = basnamn + TRYCK_SUFFIX + "_1.pdf";
                    var forstaSokv = PDF_MAPP + forstaNamn;
                    log("[exporterar PDF: " + forstaNamn + "]");
                    exporteraPDF(mergeDoc, forstaSokv);
                    log("PDF: " + forstaNamn + " (1/" + exemplar + ")");
                    exemplarMap[basnamn + TRYCK_SUFFIX + "_1"] = 1;

                    var forstaFil = new File(forstaSokv);
                    for (var nr = 2; nr <= exemplar; nr++) {
                        var kopiaNamn = basnamn + TRYCK_SUFFIX + "_" + nr + ".pdf";
                        var kopiaSokv = PDF_MAPP + kopiaNamn;
                        try { new File(kopiaSokv).remove(); } catch(e) {}
                        forstaFil.copy(kopiaSokv);
                        log("PDF: " + kopiaNamn + " (kopia " + nr + "/" + exemplar + ")");
                        exemplarMap[basnamn + TRYCK_SUFFIX + "_" + nr] = 1;
                    }
                } else {
                    // Har _exemplar_-ramar: första iterationen skrev redan "S1".
                    // Radera automatiserings-textramar FÖRE loopen så alla
                    // kopior blir rena (tidigare kördes det bara inför sista
                    // kopian → kodrutor visibles på kopia 1..N-1).
                    var borttagna = taBortFargkoder(mergeDoc);
                    log("  Tog bort " + borttagna + " automatiserings-textramar");

                    for (var nr = 1; nr <= exemplar; nr++) {
                        if (nr > 1) {
                            var skrivet = skrivExemplarNr(mergeDoc, nr);
                            log("  Exemplar " + nr + ": skrev \"S" + nr + "\" i " +
                                skrivet + " _exemplar_-ram(ar)");
                        } else {
                            log("  Exemplar 1: skrev \"S1\" i " + antalExemplar +
                                " _exemplar_-ram(ar)");
                        }

                        var pdfNamn = basnamn + TRYCK_SUFFIX + "_" + nr + ".pdf";
                        log("[exporterar PDF: " + pdfNamn + "]");
                        exporteraPDF(mergeDoc, PDF_MAPP + pdfNamn);
                        log("PDF: " + pdfNamn + " (exemplar " + nr + "/" + exemplar + ")");

                        // Varje _N-PDF är unik -> 1 exemplar var i MASTER
                        exemplarMap[basnamn + TRYCK_SUFFIX + "_" + nr] = 1;
                    }
                }
            } else {
                var borttagna = taBortFargkoder(mergeDoc);
                log("Tog bort " + borttagna + " automatiserings-textramar");

                var pdfNamnEnkel = basnamn + TRYCK_SUFFIX + ".pdf";
                log("[exporterar PDF: " + pdfNamnEnkel + "]");
                exporteraPDF(mergeDoc, PDF_MAPP + pdfNamnEnkel);
                log("PDF: " + pdfNamnEnkel);

                exemplarMap[basnamn + TRYCK_SUFFIX] = 1;
            }

            log("[stänger dokument]");
            try { mergeDoc.close(SaveOptions.NO); } catch(e) {}
            try { doc.close(SaveOptions.NO); } catch(e) {}
            var filSek = Math.round((new Date() - filStart) / 1000);
            lyckades.push(basnamn + " (x" + exemplar + ", " + filSek + "s)");
            log("OK: " + basnamn + " (tog " + filSek + " sekunder)");

            // Tvinga minnesrensning mellan filer — undviker ackumulering
            // som kan göra att InDesign fryser efter många filer.
            try { $.gc(); } catch(e) {}

        } catch(e) {
            var felrad = basnamn + ": " + e.message + " (rad " + e.line + ")";
            misslyckades.push(felrad);
            log("FEL: " + felrad);
            try { app.activeDocument.close(SaveOptions.NO); } catch(e2) {}
            try { doc.close(SaveOptions.NO); } catch(e3) {}
        }

        if (tempFil) { try { tempFil.remove(); } catch(e) {} }
    }
}

app.linkingPreferences.checkLinksAtOpen = true;
app.scriptPreferences.userInteractionLevel = origInteraction;

log("\n=== Exemplar-map ===");
skrivExemplarMap();

log("\n=== Interfoliering ===");
if (TRYCK_MODE) {
    log("  Hoppas över i tryck-läge (tryckfärdiga PDF:er är redan monterade)");
} else if (lyckades.length > 0) {
    körInterfoliering();
} else {
    log("  Inga lyckade PDF:er – hoppar interfoliering");
}

// ── Loggfil (redan skriven inkrementellt — sista flushen här) ────────────
log("\nSlut: " + new Date().toString());
flushLogg();

// ── Rapport ───────────────────────────────────────────────────────────────
var rapport = "=== KLAR ===\n\nLyckades: " + lyckades.length + "\n";
for (var i = 0; i < lyckades.length; i++) rapport += "  \u2713 " + lyckades[i] + "\n";

if (fallbackNamn.length > 0) {
    rapport += "\n\u26A0  " + fallbackNamn.length + " filer saknar post i utskrift_config.json";
    rapport += "\n   (fick fallback-värdet 1 exemplar):\n";
    for (var i = 0; i < fallbackNamn.length; i++) rapport += "  ! " + fallbackNamn[i] + "\n";
    rapport += "\n   Lägg till dessa i Bilder\\färgschema.xlsx, fliken 'Utskrift'.\n";
}

rapport += "\nHoppades (ingen CSV): " + hoppades.length + "\n";
for (var i = 0; i < hoppades.length; i++) rapport += "  \u2013 " + hoppades[i] + "\n";
if (misslyckades.length > 0) {
    rapport += "\nFel: " + misslyckades.length + "\n";
    for (var i = 0; i < misslyckades.length; i++) rapport += "  \u2717 " + misslyckades[i] + "\n";
}
rapport += "\nExemplar-map: " + exemplarMapFil.fsName;
rapport += "\nKombinerade PDF:er: " + PDF_MAPP + "Kombinerade\\";
rapport += "\nLogg: " + loggFilSokv;
alert(rapport);

