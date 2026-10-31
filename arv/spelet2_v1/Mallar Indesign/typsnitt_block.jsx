// ═══════════════════════════════════════════════════════════════
// OBSOLET — logiken är integrerad i farglagg_projektkort.jsx v14+.
// Denna fil körs inte längre av master_kortproduktion.jsx.
// Den ligger kvar som referens / backup och kan raderas.
// ───────────────────────────────────────────────────────────────
// TYPSNITT – läser typsnitt_config.json och sätter font per ram
// ═══════════════════════════════════════════════════════════════

// ── Läs typsnitt_config.json ────────────────────────────────────
function lasTypsnittConfig() {
    // Filen ligger bredvid skriptet (i SPELET 2\)
    var scriptDir = File($.fileName).parent.parent; // Scripts\User → SPELET 2
    var jsonFil   = File(scriptDir + "/typsnitt_config.json");

    // Fallback om filen saknas
    var cfg = {
        rubrik_font:     "Minion Pro",
        rubrik_style:    "Bold",
        brodtext_font:   "Minion Pro",
        brodtext_style:  "Regular",
        storlek_troskel: 14
    };

    if (!jsonFil.exists) {
        $.writeln("typsnitt_config.json saknas – använder fallback-typsnitt");
        return cfg;
    }

    try {
        jsonFil.open("r");
        var innehall = jsonFil.read();
        jsonFil.close();

        // Enkel JSON-parser (ExtendScript saknar JSON.parse i äldre versioner)
        cfg.rubrik_font     = innehall.match(/"rubrik_font"\s*:\s*"([^"]+)"/)[1];
        cfg.rubrik_style    = innehall.match(/"rubrik_style"\s*:\s*"([^"]+)"/)[1];
        cfg.brodtext_font   = innehall.match(/"brodtext_font"\s*:\s*"([^"]+)"/)[1];
        cfg.brodtext_style  = innehall.match(/"brodtext_style"\s*:\s*"([^"]+)"/)[1];
        cfg.storlek_troskel = parseFloat(
            innehall.match(/"storlek_troskel"\s*:\s*([\d.]+)/)[1]
        );
    } catch(e) {
        $.writeln("Fel vid läsning av typsnitt_config.json: " + e);
    }
    return cfg;
}

// ── Sätt typsnitt på textramar i ett spread ─────────────────────
function sattTypsnitt(spread, cfg) {
    var troskel = cfg.storlek_troskel;

    for (var f = 0; f < spread.allPageItems.length; f++) {
        var obj = spread.allPageItems[f];
        if (!(obj instanceof TextFrame)) continue;

        try {
            var texts = obj.texts.everyItem().getElements();
            if (!texts.length) continue;

            // Avgör roll baserat på första teckens punktstorlek
            var forstaStorlek = obj.texts[0].characters[0].pointSize;
            var arRubrik = (forstaStorlek >= troskel);

            var fontNamn = arRubrik ? cfg.rubrik_font  : cfg.brodtext_font;
            var fontStil = arRubrik ? cfg.rubrik_style : cfg.brodtext_style;

            // Sätt på alla tecken i ramen
            obj.texts.everyItem().appliedFont       = fontNamn;
            obj.texts.everyItem().fontStyle          = fontStil;

        } catch(e) {
            // Hoppa tyst över låsta/masterpage-ramar
        }
    }
}

// ── Anrop (lägg in i huvudflödet efter att färger satts) ────────
var TYPSNITT = lasTypsnittConfig();
sattTypsnitt(targetSpread, TYPSNITT);
// ════════════════════════════════════════════════════════════════

