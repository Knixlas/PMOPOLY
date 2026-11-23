// master_tryckbart.jsx v1
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
        for (var s = 0; s < mergeDoc.spreads.length; s++) {
            var spread = mergeDoc.spreads[s];
            var allaItems = spread.allPageItems;

            // Samla _kortram
            var kortramar = [];
            for (var i = 0; i < allaItems.length; i++) {
                if (allaItems[i].name === "_kortram") {
                    kortramar.push(allaItems[i]);
                }
            }
            if (kortramar.length < 2) continue;

            // Hitta unika kolumn-x och rad-y (med tolerans)
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

            var xMids = [];
            var yMids = [];
            for (var k = 0; k < kortramar.length; k++) {
                var b = kortramar[k].geometricBounds;
                xMids.push((b[1] + b[3]) / 2);
                yMids.push((b[0] + b[2]) / 2);
            }
            var kolumnX = unikaVarden(xMids, 5);  // 5pt tolerans
            var radY    = unikaVarden(yMids, 5);

            // Steg 1: beräkna shift per item (baserat på ORIGINAL positioner)
            var shifts = [];
            for (var i = 0; i < allaItems.length; i++) {
                var it = allaItems[i];
                try {
                    var ib = it.geometricBounds;
                    var icx = (ib[1] + ib[3]) / 2;
                    var icy = (ib[0] + ib[2]) / 2;

                    // Hitta närmaste kortram — bara items nära EN kortram flyttas
                    var bestK = -1;
                    var minD = Infinity;
                    for (var k = 0; k < kortramar.length; k++) {
                        var kb = kortramar[k].geometricBounds;
                        var kcx = (kb[1] + kb[3]) / 2;
                        var kcy = (kb[0] + kb[2]) / 2;
                        var dx = kcx - icx;
                        var dy = kcy - icy;
                        var d2 = dx * dx + dy * dy;
                        if (d2 < minD) { minD = d2; bestK = k; }
                    }
                    if (bestK < 0) continue;

                    // Identifiera kolumn/rad-index för detta _kortram
                    var kb2 = kortramar[bestK].geometricBounds;
                    var kcx = (kb2[1] + kb2[3]) / 2;
                    var kcy = (kb2[0] + kb2[2]) / 2;

                    var colIdx = 0;
                    for (var xi = 0; xi < kolumnX.length; xi++) {
                        if (Math.abs(kolumnX[xi] - kcx) < 5) { colIdx = xi; break; }
                    }
                    var rowIdx = 0;
                    for (var yi = 0; yi < radY.length; yi++) {
                        if (Math.abs(radY[yi] - kcy) < 5) { rowIdx = yi; break; }
                    }

                    var dx2 = colIdx * extraGap_pt;
                    var dy2 = rowIdx * extraGap_pt;
                    if (dx2 === 0 && dy2 === 0) continue;
                    shifts.push({ item: it, dx: dx2, dy: dy2 });
                } catch(e) {}
            }

            // Steg 2: applicera shifts
            for (var i = 0; i < shifts.length; i++) {
                try {
                    shifts[i].item.move(
                        [shifts[i].dx, shifts[i].dy],
                        CoordinateSpaces.PARENT_COORDINATES
                    );
                    totalSpridda++;
                } catch(e) {}
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

        // ── 1. Förstora varje _bakgrund_*-ruta med BLEED_PT på varje sida ──
        //    Detta blir utfallet. INGEN ny rektangel skapas — vi expanderar
        //    den befintliga, så färgen som farglagg satt bevaras automatiskt.
        for (var b = 0; b < bakgrundRutor.length; b++) {
            var br = bakgrundRutor[b];
            try {
                var bds = br.geometricBounds;  // [y1, x1, y2, x2]
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
                var y1 = kb[0], x1 = kb[1], y2 = kb[2], x2 = kb[3];
                // Övre vänster (x1, y1)
                skapaLinje(sida, x1 - offset_pt - markLen_pt, y1, x1 - offset_pt, y1);
                skapaLinje(sida, x1, y1 - offset_pt - markLen_pt, x1, y1 - offset_pt);
                // Övre höger (x2, y1)
                skapaLinje(sida, x2 + offset_pt, y1, x2 + offset_pt + markLen_pt, y1);
                skapaLinje(sida, x2, y1 - offset_pt - markLen_pt, x2, y1 - offset_pt);
                // Nedre vänster (x1, y2)
                skapaLinje(sida, x1 - offset_pt - markLen_pt, y2, x1 - offset_pt, y2);
                skapaLinje(sida, x1, y2 + offset_pt, x1, y2 + offset_pt + markLen_pt);
                // Nedre höger (x2, y2)
                skapaLinje(sida, x2 + offset_pt, y2, x2 + offset_pt + markLen_pt, y2);
                skapaLinje(sida, x2, y2 + offset_pt, x2, y2 + offset_pt + markLen_pt);
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
    app.doScript(masterFil, ScriptLanguage.JAVASCRIPT);
} else {
    alert("master_kortproduktion.jsx saknas i samma mapp som detta skript.\n" +
          "Sökväg som söktes: " + masterFil.fsName);
}

