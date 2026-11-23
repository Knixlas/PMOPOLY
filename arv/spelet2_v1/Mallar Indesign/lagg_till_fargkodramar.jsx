// lagg_till_fargkodramar.jsx
// Lägger till _linecolor och _fillcolor textramar på pasteboardet
// Hoppar över om de redan finns

var doc = app.activeDocument;
var sida = doc.pages[0];

// Placera på pasteboardet till höger om sidan
var sidBounds = sida.bounds; // [y1, x1, y2, x2]
var startX = sidBounds[3] + 10;  // 10mm till höger om sidan
var startY = sidBounds[0];       // Samma y som sidans överkant

var skapade = [];
var hoppade = [];

// Kontrollera om en ram med givet namn redan finns
function finnsFran(namn) {
    var items = doc.allPageItems;
    for (var i = 0; i < items.length; i++) {
        if (items[i].name === namn) return true;
    }
    return false;
}

function skapaRam(namn, x, y, platshallare) {
    if (finnsFran(namn)) {
        hoppade.push(namn);
        return;
    }
    var ram = sida.textFrames.add({
        geometricBounds: [y, x, y + 8, x + 30],  // [y1, x1, y2, x2] i mm
        fillColor:  doc.swatches.itemByName("None"),
        strokeColor: doc.swatches.itemByName("Black")
    });
    ram.name = namn;
    ram.contents = platshallare;
    skapade.push(namn);
}

skapaRam("_linecolor", startX,      startY,      "«line_color»");
skapaRam("_fillcolor", startX + 35, startY,      "«fill_color»");

var msg = "";
if (skapade.length > 0)  msg += "Skapade: " + skapade.join(", ") + "\n";
if (hoppade.length > 0)  msg += "Fanns redan: " + hoppade.join(", ") + "\n";
if (!msg) msg = "Inget att göra.";

alert(msg.trim());

