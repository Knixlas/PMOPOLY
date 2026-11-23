// master_tryckbart.jsx v1.1 SAFE
//
// Producerar tryckbara PDF:er: samma innehåll som master_kortproduktion.jsx
// men med utfall (3mm) + adaptiva skärmärken per kort.
//
// Hur det fungerar:
//   1. Sätter TRYCK_MODE = true (ändrar output till PDF\Tryckbara\ + suffix _tryck)
//   2. Definierar onTryckPrep() som master anropar efter farglagg
//   3. Kör master_kortproduktion.jsx via doScript
//
// KRAV PÅ MALLARNA:
//   - Varje bildsida.indd + textsida.indd MÅSTE ha ett element döpt
//     "_kortram" per kort-template (rektangel utan fyllning eller linje,
//     placerad på kortets skärlinje). Multi-record merge replikerar den.
//
// Utfall: 3 mm (färgad rektangel bakom varje kort, fylls med _fillcolor
//         vid 10% opacitet — samma logik som farglagg-skriptet).
// Skärmärken: adaptiv längd baserat på mellanrum mellan kort.
//   - ≥ 14 mm gap: 4 mm märken (standard)
//   - 6-14 mm gap: automatiskt kortare märken
//   - < 6 mm gap: 1 mm märken (minimal, fungerar men inte standard)

TRYCK_MODE = true;

// Konstanter för tryckbart (åtkomliga från onTryckPrep)
var TRYCK_BLEED_MM       = 3;
var TRYCK_CROP_LEN_MM    = 4;
var TRYCK_CROP_OFFSET_MM = 3;
var TRYCK_CROP_LEN_MIN_MM = 1;

// Extra mellanrum (mm) som läggs MELLAN korten i tryck-läge. Sprider isär
// korten så tryckeriet får plats för skärmärken + fritt snitt. Normala
// körningar (master_kortproduktion) påverkas INTE. Sätt till 0 för att
// behålla mallens ursprungliga layout.
var TRYCK_EXTRA_GAP_MM   = 10;
// Felsökning: sätt till 0 för att helt hoppa över isärflyttning av kort.
// Den tidigare versionen försökte flytta spread.allPageItems, dvs även objekt INUTI grupper.
// Denna SAFE-version flyttar bara top-level pageItems och använder korrekt move-syntax.

// Bleed-rektangeln ska matcha kortets 10%-tintade bakgrund (samma som
// farglagg skapar i single-record-mode). Istället för att använda 10%
// opacitet (som staplas vid överlapp) förberäknar vi den tintade RGB:n
// och använder 100% opacitet.
var TRYCK_TINT_PERCENT   = 10;  // matchar farglagg
var TRYCK_PAPPER_RGB     = [255, 255, 255];  // vitt papper

// ── onTryckPrep: körs av master_kortproduktion.jsx efter farglagg ──
onTryckPrep = function(mergeDoc) {
    var MM_TO_PT = 72.0 / 25.4;
    var BLEED_PT = TRYCK_BLEED_MM * MM_TO_PT;

    var svart = null;
    try { svart = mergeDoc.swatches.itemByName("Black"); } catch(e) {}
    var ingen = null;
    try { ingen = mergeDoc.swatches.itemByName("None"); } catch(e) {}

    function hex2rgb(h) {
        h = h.replace("#", "");
        return [parseInt(h.substring(0,2),16),
                parseInt(h.substring(2,4),16),
                parseInt(h.substring(4,6),16)];
    }
    // Beräkna tintad RGB: motsvarar att lägga hex vid TRYCK_TINT_PERCENT%
    // opacitet ovanpå vitt papper — men som en färdig RGB så vi slipper
    // opacitets-staplingsproblem när bleed-rektanglar överlappar.
    function tintadRgb(hex) {
        var rgb = hex2rgb(hex);
        var t = TRYCK_TINT_PERCENT / 100;
        var pR = TRYCK_PAPPER_RGB[0];
        var pG = TRYCK_PAPPER_RGB[1];
        var pB = TRYCK_PAPPER_RGB[2];
        return [
            Math.round((1 - t) * pR + t * rgb[0]),
            Math.round((1 - t) * pG + t * rgb[1]),
            Math.round((1 - t) * pB + t * rgb[2])
        ];
    }
    // Skapar färg från hex — tintVariant=true ger 10%-tintad version
    function skapaFarg(hex, tintVariant) {
        var rgb = tintVariant ? tintadRgb(hex) : hex2rgb(hex);
        var suffix = tintVariant ? "_TINT" : "";
        var namn = "TRYCK_" + hex.replace("#","").toUpperCase() + suffix;
        try {
            var c = mergeDoc.colors.itemByName(namn);
            if (c.isValid) return c;
        } catch(e) {}
        var c = mergeDoc.colors.add();
        c.name = namn;
        c.model = ColorModel.PROCESS;
        c.space = ColorSpace.RGB;
        c.colorValue = [rgb[0], rgb[1], rgb[2]];
        return c;
    }
    function skapaLinje(page, x1, y1, x2, y2) {
        var l = page.graphicLines.add({
            strokeColor: svart,
            strokeWeight: "0.25pt"
        });
        l.paths[0].entirePath = [[x1, y1], [x2, y2]];
    }

    // Minsta gap mellan intilliggande _kortram-rektanglar på spread
    function beraknaMinGap(ramar) {
        if (ramar.length < 2) return Infinity;
        var minGap = Infinity;
        for (var i = 0; i < ramar.length; i++) {
            var bi = ramar[i].geometricBounds;  // [y1, x1, y2, x2]
            for (var j = i + 1; j < ramar.length; j++) {
                var bj = ramar[j].geometricBounds;
                var yOver = !(bi[2] <= bj[0] || bj[2] <= bi[0]);
                var xOver = !(bi[3] <= bj[1] || bj[3] <= bi[1]);
                if (yOver) {
                    var dx = Math.max(bj[1] - bi[3], bi[1] - bj[3]);
                    if (dx > 0 && dx < minGap) minGap = dx;
                }
                if (xOver) {
                    var dy = Math.max(bj[0] - bi[2], bi[0] - bj[2]);
                    if (dy > 0 && dy < minGap) minGap = dy;
                }
            }
        }
        return minGap;
    }

    // Hitta närmaste _fillcolor-datapunkt relativt kortram-center
    function narmasteFill(bounds, fillPunkter) {
        var cx = (bounds[1] + bounds[3]) / 2;
        var cy = (bounds[0] + bounds[2]) / 2;
        var best = null, minD = Infinity;
        for (var i = 0; i < fillPunkter.length; i++) {
            var dx = fillPunkter[i].mid.x - cx;
            var dy = fillPunkter[i].mid.y - cy;
            var d = Math.sqrt(dx*dx + dy*dy);
            if (d < minD) { minD = d; best = fillPunkter[i]; }
        }
        return best;
    }

    // ── Sprida kort-positioner för tryck ────────────────────────────
    // Ökar mellanrummet MELLAN korten (utan att röra innehållet inom
    // varje kort). Använder _kortram-positioner för att identifiera
    // kolumner/rader, och shiftar alla items som tillhör varje kort.
    function spridaKortForTryck(mergeDoc, extraGap_pt) {
        var totalSpridda = 0;
        var CARD_MARGIN_PT = 12; // marginal runt _kortram för att avgöra om ett objekt hör till kortet

        function getElementsSafe(collection) {
            try { return collection.everyItem().getElements(); } catch(e) {}
            var arr = [];
            try {
                for (var i = 0; i < collection.length; i++) arr.push(collection[i]);
            } catch(e2) {}
            return arr;
        }

        function unikaVarden(vals, tolerans) {
            var result = [];
            for (var i = 0; i < vals.length; i++) {
                var fann = false;
                for (var j = 0; j < result.length; j++) {
                    if (Math.abs(vals[i] - result[j]) < tolerans) { fann = true; break; }
                }
                if (!fann) result.push(vals[i]);
            }
            result.sort(function(a, b) { return a - b; });
            return result;
        }

        for (var s = 0; s < mergeDoc.spreads.length; s++) {
            var spread = mergeDoc.spreads[s];

            // Samla _kortram via allPageItems, men använd dem ENDAST som positionsreferenser.
            // Att flytta allPageItems är farligt eftersom samlingen innehåller både grupper och gruppbarn.
            var alla = spread.allPageItems;
            var kortramData = [];
            for (var i = 0; i < alla.length; i++) {
                try {
                    if (alla[i].name !== "_kortram") continue;
                    var b = alla[i].geometricBounds;
                    kortramData.push({
                        item: alla[i],
                        y1: b[0], x1: b[1], y2: b[2], x2: b[3],
                        cx: (b[1] + b[3]) / 2,
                        cy: (b[0] + b[2]) / 2
                    });
                } catch(e) {}
            }
            if (kortramData.length < 2) continue;

            var xMids = [], yMids = [];
            for (var k = 0; k < kortramData.length; k++) {
                xMids.push(kortramData[k].cx);
                yMids.push(kortramData[k].cy);
            }
            var kolumnX = unikaVarden(xMids, 5);
            var radY    = unikaVarden(yMids, 5);

            // Flytta bara top-level items. Grupper flyttas som EN enhet; deras barn lämnas i fred.
            // Det minskar både risken för dubbel-/trippelflytt och mängden InDesign-objekt som manipuleras.
            var topItems = getElementsSafe(spread.pageItems);
            var shifts = [];

            for (var ti = 0; ti < topItems.length; ti++) {
                var it = topItems[ti];
                try {
                    if (!it.isValid) continue;
                    if (it.locked) continue;

                    var ib = it.geometricBounds;
                    var icx = (ib[1] + ib[3]) / 2;
                    var icy = (ib[0] + ib[2]) / 2;

                    var best = null;
                    var minD = Infinity;
                    for (var kk = 0; kk < kortramData.length; kk++) {
                        var kd0 = kortramData[kk];

                        // Ta bara objekt vars mittpunkt ligger i/nära en kortram.
                        // Annars riskerar sidobjekt, hjälpelement eller data-markörer att dras med.
                        var insideOrNear = (
                            icx >= kd0.x1 - CARD_MARGIN_PT && icx <= kd0.x2 + CARD_MARGIN_PT &&
                            icy >= kd0.y1 - CARD_MARGIN_PT && icy <= kd0.y2 + CARD_MARGIN_PT
                        );
                        if (!insideOrNear) continue;

                        var dd = (kd0.cx - icx) * (kd0.cx - icx) + (kd0.cy - icy) * (kd0.cy - icy);
                        if (dd < minD) { minD = dd; best = kd0; }
                    }
                    if (!best) continue;

                    var colIdx = 0;
                    for (var xi = 0; xi < kolumnX.length; xi++) {
                        if (Math.abs(kolumnX[xi] - best.cx) < 5) { colIdx = xi; break; }
                    }
                    var rowIdx = 0;
                    for (var yi = 0; yi < radY.length; yi++) {
                        if (Math.abs(radY[yi] - best.cy) < 5) { rowIdx = yi; break; }
                    }

                    var dx2 = colIdx * extraGap_pt;
                    var dy2 = rowIdx * extraGap_pt;
                    if (dx2 === 0 && dy2 === 0) continue;
                    shifts.push({ item: it, dx: dx2, dy: dy2 });
                } catch(e1) {}
            }

            for (var si = 0; si < shifts.length; si++) {
                try {
                    // Korrekt InDesign-syntax för relativ flytt:
                    // move(undefined, [dx, dy]) — inte move([dx,dy], CoordinateSpaces...).
                    shifts[si].item.move(undefined, [shifts[si].dx, shifts[si].dy]);
                    totalSpridda++;
                } catch(e2) {}
            }
        }
        return totalSpridda;
    }

    // Sprida isär kort FÖRST så efterföljande logik ser nya positioner
    var totSpridda = 0;
    if (TRYCK_EXTRA_GAP_MM > 0) {
        totSpridda = spridaKortForTryck(mergeDoc, TRYCK_EXTRA_GAP_MM * MM_TO_PT);
    }

    var totKort = 0, totBleed = 0, totMarks = 0;
    var perSpreadLogg = [];

    for (var s = 0; s < mergeDoc.spreads.length; s++) {
        var spread = mergeDoc.spreads[s];
        var sida   = spread.pages[0];

        // Samla _kortram + _bakgrund_*-rutor (visuella bakgrundselement).
        // Vi förstorar de befintliga rektanglarna istället för att skapa nya.
        var kortramar = [];
        var bakgrundRutor = [];  // _bakgrund_* (utom datapunkten _bakgrund_color)
        var items = spread.allPageItems;
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            var namn = "";
            try { namn = it.name || ""; } catch(e) {}
            if (namn === "_kortram") {
                kortramar.push(it);
            } else if (namn.indexOf("_bakgrund_") === 0 && namn !== "_bakgrund_color") {
                bakgrundRutor.push(it);
            } else if (namn.indexOf("_bakskede_") === 0 && namn !== "_bakskede_color") {
                bakgrundRutor.push(it);
            }
        }

        if (kortramar.length === 0) {
            perSpreadLogg.push("spread " + s + ": inga _kortram");
            continue;
        }

        // Adaptiv mark-längd + offset baserat på minsta gap
        var minGap = beraknaMinGap(kortramar);
        var markLen_pt = TRYCK_CROP_LEN_MM * MM_TO_PT;
        var offset_pt  = TRYCK_CROP_OFFSET_MM * MM_TO_PT;

        if (minGap !== Infinity) {
            var halvGap = minGap / 2;
            // Båda grannkort behöver plats för offset + mark + säkerhetsbuffert 1mm
            var tillgangligt = halvGap - 1 * MM_TO_PT;
            if (tillgangligt < offset_pt + markLen_pt) {
                // Krymp offset först, sen mark
                var kravMark = TRYCK_CROP_LEN_MIN_MM * MM_TO_PT;
                if (tillgangligt >= kravMark + 1 * MM_TO_PT) {
                    offset_pt = Math.max(0, tillgangligt - markLen_pt);
                    if (offset_pt < 0.5 * MM_TO_PT) {
                        offset_pt = 0.5 * MM_TO_PT;
                        markLen_pt = Math.max(kravMark, tillgangligt - offset_pt);
                    }
                } else {
                    markLen_pt = kravMark;
                    offset_pt  = Math.max(0, tillgangligt - markLen_pt);
                }
            }
        }

        perSpreadLogg.push(
            "spread " + s + ": " + kortramar.length + " _kortram, " +
            bakgrundRutor.length + " _bakgrund_rutor, " +
            "gap=" + (minGap === Infinity ? "∞" : (minGap / MM_TO_PT).toFixed(1)) + "mm, " +
            "mark=" + (markLen_pt / MM_TO_PT).toFixed(1) + "mm, " +
            "offset=" + (offset_pt / MM_TO_PT).toFixed(1) + "mm"
        );

        // ── 1. Förstora varje bakgrundsruta med BLEED_PT på varje sida ──
        //    Detta blir utfallet. INGEN ny rektangel skapas — vi expanderar
        //    den befintliga, så färgen som farglagg satt bevaras automatiskt.
        //    SKYDD: bara rutor som är ≥ 50% av kortets yta i båda dimensionerna
        //    förstoras. Det utesluter små accent-stripes namngivna _bakskede_*
        //    som inte är heltäckande bakgrund.
        //
        //    OPTIMERING: cacha _kortram-bounds en gång. geometricBounds-läs
        //    är dyra i InDesign-skripting. Tidigare räknades kortramens
        //    bounds om för varje bakgrundsruta — för spreads med många
        //    rutor blev det extremt långsamt.
        var kortramData = [];
        for (var ki0 = 0; ki0 < kortramar.length; ki0++) {
            try {
                var kbb0 = kortramar[ki0].geometricBounds;
                kortramData.push({
                    cx: (kbb0[1] + kbb0[3]) / 2,
                    cy: (kbb0[0] + kbb0[2]) / 2,
                    w: kbb0[3] - kbb0[1],
                    h: kbb0[2] - kbb0[0]
                });
            } catch(e0) {}
        }

        for (var b = 0; b < bakgrundRutor.length; b++) {
            var br = bakgrundRutor[b];
            try {
                var bds = br.geometricBounds;  // [y1, x1, y2, x2]
                var rutaW = bds[3] - bds[1];
                var rutaH = bds[2] - bds[0];
                var rutaCx = (bds[1] + bds[3]) / 2;
                var rutaCy = (bds[0] + bds[2]) / 2;
                var nearK = null;
                var nearD = Infinity;
                for (var ki = 0; ki < kortramData.length; ki++) {
                    var kd = kortramData[ki];
                    var dd = Math.pow(kd.cx - rutaCx, 2) + Math.pow(kd.cy - rutaCy, 2);
                    if (dd < nearD) { nearD = dd; nearK = kd; }
                }
                if (nearK) {
                    if (rutaW < nearK.w * 0.5 || rutaH < nearK.h * 0.5) {
                        continue;
                    }
                }
                br.geometricBounds = [
                    bds[0] - BLEED_PT,
                    bds[1] - BLEED_PT,
                    bds[2] + BLEED_PT,
                    bds[3] + BLEED_PT
                ];
                totBleed++;
            } catch(e) {}
        }

        // ── 2. Rita skärmärken vid varje _kortram-hörn ──────────────────
        for (var k = 0; k < kortramar.length; k++) {
            var kr = kortramar[k];
            var kb = kr.geometricBounds;  // [y1, x1, y2, x2]

            try {
                // Rita märken på samma sida som _kortram om dokumentet har facing pages.
                // Fallback till spread.pages[0] för enkelsidiga/udda fall.
                var markPage = sida;
                try {
                    if (kr.parentPage && kr.parentPage.isValid) markPage = kr.parentPage;
                } catch(ePage) {}

                var y1 = kb[0], x1 = kb[1], y2 = kb[2], x2 = kb[3];
                // Övre vänster (x1, y1)
                skapaLinje(markPage, x1 - offset_pt - markLen_pt, y1, x1 - offset_pt, y1);
                skapaLinje(markPage, x1, y1 - offset_pt - markLen_pt, x1, y1 - offset_pt);
                // Övre höger (x2, y1)
                skapaLinje(markPage, x2 + offset_pt, y1, x2 + offset_pt + markLen_pt, y1);
                skapaLinje(markPage, x2, y1 - offset_pt - markLen_pt, x2, y1 - offset_pt);
                // Nedre vänster (x1, y2)
                skapaLinje(markPage, x1 - offset_pt - markLen_pt, y2, x1 - offset_pt, y2);
                skapaLinje(markPage, x1, y2 + offset_pt, x1, y2 + offset_pt + markLen_pt);
                // Nedre höger (x2, y2)
                skapaLinje(markPage, x2 + offset_pt, y2, x2 + offset_pt + markLen_pt, y2);
                skapaLinje(markPage, x2, y2 + offset_pt, x2, y2 + offset_pt + markLen_pt);
                totMarks += 8;
            } catch(e) {}

            totKort++;
        }
    }

    if (totSpridda > 0) {
        perSpreadLogg.unshift("Spred isär " + totSpridda + " items med " +
                              TRYCK_EXTRA_GAP_MM + "mm extra gap");
    }
    return {
        kort: totKort,
        bleed: totBleed,
        marks: totMarks,
        logg: perSpreadLogg
    };
};

// ── Kör master_kortproduktion.jsx ────────────────────────────────────
var thisFil = new File($.fileName);
var masterFil = new File(thisFil.parent.fsName + "/master_kortproduktion.jsx");

if (masterFil.exists) {
    var _oldRedraw = app.scriptPreferences.enableRedraw;
    app.scriptPreferences.enableRedraw = false;
    try {
        app.doScript(masterFil, ScriptLanguage.JAVASCRIPT, undefined, UndoModes.FAST_ENTIRE_SCRIPT, "Skapa tryckbar kortproduktion");
    } finally {
        app.scriptPreferences.enableRedraw = _oldRedraw;
    }
} else {
    alert("master_kortproduktion.jsx saknas i samma mapp som detta skript.\n" +
          "Sökväg som söktes: " + masterFil.fsName);
}

