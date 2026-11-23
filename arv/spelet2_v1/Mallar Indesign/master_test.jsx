// master_test.jsx v2
//
// Snabb-test: kör master_kortproduktion.jsx (eller master_tryckbart.jsx)
// PÅ EN ELLER NÅGRA FILER — för felsökning när du inte vill vänta på
// hela flödet. Visar en dialog där du väljer filter + tryck-läge.

// ── Dialog ───────────────────────────────────────────────────────────

// Återanvänd senaste inställning om sådan finns (spars mellan körningar)
var FORRA_FILTER = (typeof $.global.senasteTestFilter !== "undefined")
    ? $.global.senasteTestFilter : "PU_personal";
var FORRA_TRYCK = (typeof $.global.senasteTryckMode !== "undefined")
    ? $.global.senasteTryckMode : true;

var dlg = new Window("dialog", "Master-test");
dlg.orientation = "column";
dlg.alignChildren = "fill";
dlg.margins = 16;
dlg.spacing = 10;

dlg.add("statictext", undefined,
    "Kör master på EN eller NÅGRA filer för snabb felsökning.");

// ── Filter-grupp ──
var filGrupp = dlg.add("panel", undefined, "Vilka filer?");
filGrupp.orientation = "column";
filGrupp.alignChildren = "left";
filGrupp.margins = 12;
filGrupp.spacing = 8;

filGrupp.add("statictext", undefined,
    "Delnamn på fil (tomt = ALLA filer). Matchar case-insensitive:");

var filInput = filGrupp.add("edittext", undefined, FORRA_FILTER);
filInput.characters = 35;

var exempelTxt = filGrupp.add("statictext", undefined,
    "Ex: 'PU_personal' → bild+text,  'PL_leverant' → leverantörer");
exempelTxt.graphics.font = ScriptUI.newFont(exempelTxt.graphics.font.name, "ITALIC", 10);

// ── Läge-grupp ──
var lageGrupp = dlg.add("panel", undefined, "Läge");
lageGrupp.orientation = "column";
lageGrupp.alignChildren = "left";
lageGrupp.margins = 12;

var tryckCheck = lageGrupp.add("checkbox", undefined,
    "Tryck-läge (utfall + skärmärken → PDF\\Tryckbara\\)");
tryckCheck.value = FORRA_TRYCK;

lageGrupp.add("statictext", undefined,
    "Avmarkera för vanlig arbetskopia → PDF\\");

// ── Knappar ──
var btnGrupp = dlg.add("group");
btnGrupp.alignment = "right";
btnGrupp.spacing = 8;

var avbrytBtn = btnGrupp.add("button", undefined, "Avbryt", {name: "cancel"});
var korBtn = btnGrupp.add("button", undefined, "Kör", {name: "ok"});

// ── Kör ──
if (dlg.show() !== 1) {
    // Avbryt
} else {
    // Spara val för nästa gång
    $.global.senasteTestFilter = filInput.text;
    $.global.senasteTryckMode  = tryckCheck.value;

    // Sätt globalerna som master läser
    DEBUG_ENDAST_FIL = filInput.text;
    TRYCK_MODE       = tryckCheck.value;

    var thisFil = new File($.fileName);
    var masterFil = new File(thisFil.parent.fsName + "/master_kortproduktion.jsx");

    if (TRYCK_MODE) {
        // Kör via tryckbart-wrappern (som definierar onTryckPrep + kör master)
        var tryckFil = new File(thisFil.parent.fsName + "/master_tryckbart.jsx");
        if (tryckFil.exists) {
            app.doScript(tryckFil, ScriptLanguage.JAVASCRIPT);
        } else {
            alert("master_tryckbart.jsx saknas. Kör master_kortproduktion istället.");
            app.doScript(masterFil, ScriptLanguage.JAVASCRIPT);
        }
    } else {
        if (masterFil.exists) {
            app.doScript(masterFil, ScriptLanguage.JAVASCRIPT);
        } else {
            alert("master_kortproduktion.jsx saknas i samma mapp.");
        }
    }
}

