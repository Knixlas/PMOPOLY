// lagg_till_fargkodramar_alla.jsx
// Kör igenom alla .indd-filer i spelmapparna och lägger till
// _linecolor och _fillcolor på pasteboardet om de saknas.

var ROT = "/c/Users/niklas.sviden/OneDrive - \u00c5ke Sundvalls Byggnads AB/SPELET 2";

var MAPPAR = [
    ROT + "/1. Projektutveckling",
    ROT + "/2. Planering",
    ROT + "/3. Genomf\u00f6rande",
    ROT + "/4. F\u00f6rvaltning"
];

var skapade_totalt = 0;
var hoppade_totalt = 0;
var filer_totalt   = 0;
var logg = [];

function finnsFran(doc, namn) {
    var items = doc.allPageItems;
    for (var i = 0; i < items.length; i++) {
        if (items[i].name === namn) return true;
    }
    return false;
}

function skapaRam(doc, namn, x, y, platshallare) {
    if (finnsFran(doc, namn)) return false;
    var sida = doc.pages[0];
    var ram = sida.textFrames.add({
        geometricBounds: [y, x, y + 8, x + 30],
        fillColor:   doc.swatches.itemByName("None"),
        strokeColor: doc.swatches.itemByName("Black")
    });
    ram.name = namn;
    ram.contents = platshallare;
    return true;
}

function behandlaFil(path) {
    var f = File(path);
    if (!f.exists) return;

    var doc;
    var varOppen = false;

    // Kolla om redan öppen
    for (var i = 0; i < app.documents.length; i++) {
        if (app.documents[i].fullName.toString() === f.fsName) {
            doc = app.documents[i];
            varOppen = true;
            break;
        }
    }

    if (!doc) {
        doc = app.open(f, false); // false = öppna utan att visa
    }

    var sida    = doc.pages[0];
    var bounds  = sida.bounds;
    var startX  = bounds[3] + 10;
    var startY  = bounds[0];

    var skapadeHar = 0;
    if (skapaRam(doc, "_linecolor", startX,      startY, "\u00abline_color\u00bb")) skapadeHar++;
    if (skapaRam(doc, "_fillcolor", startX + 35, startY, "\u00abfill_color\u00bb")) skapadeHar++;

    var filnamn = f.name;
    if (skapadeHar > 0) {
        doc.save();
        logg.push("\u2713 " + filnamn + " (" + skapadeHar + " nya ramar)");
        skapade_totalt += skapadeHar;
    } else {
        logg.push("- " + filnamn + " (redan OK)");
        hoppade_totalt++;
    }

    if (!varOppen) doc.close(SaveOptions.NO);
    filer_totalt++;
}

// Hitta alla .indd-filer
for (var m = 0; m < MAPPAR.length; m++) {
    var mapp = Folder(MAPPAR[m]);
    if (!mapp.exists) { logg.push("! Mapp saknas: " + MAPPAR[m]); continue; }

    var filer = mapp.getFiles("*.indd");
    for (var fi = 0; fi < filer.length; fi++) {
        behandlaFil(filer[fi].fsName);
    }
}

alert("Klart!\n" + filer_totalt + " filer, " + skapade_totalt + " nya ramar\n\n" + logg.join("\n"));

