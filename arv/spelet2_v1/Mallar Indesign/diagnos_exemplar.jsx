// diagnos_exemplar.jsx
// Listar alla objekt vars namn börjar med "_exemplar_" i det aktiva
// dokumentet. Hjälper diagnosticera varför S1/S2/S3/S4 inte skrivs ut.

if (app.documents.length === 0) {
    alert("Öppna en .indd-fil först.");
} else {
    var doc = app.activeDocument;
    var rader = ["Diagnostik för: " + doc.name, ""];
    var hittat = 0;

    for (var s = 0; s < doc.spreads.length; s++) {
        var spread = doc.spreads[s];
        var items  = spread.allPageItems;
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            var namn = "";
            try { namn = it.name || ""; } catch(e) { continue; }
            if (namn.indexOf("_exemplar_") !== 0) continue;

            hittat++;
            var typ = "okänt";
            try {
                if (it instanceof TextFrame) typ = "TextFrame";
                else if (it instanceof Group) typ = "Group (" + it.allPageItems.length + " objekt)";
                else if (it instanceof Rectangle) typ = "Rectangle";
                else if (it instanceof Oval) typ = "Oval";
                else if (it instanceof Polygon) typ = "Polygon";
                else typ = it.constructor.name;
            } catch(e) {}

            var content = "";
            try {
                if (it instanceof TextFrame) {
                    content = " innehåll: \"" + (it.contents || "") + "\"";
                } else if (it.textFrames && it.textFrames.length > 0) {
                    content = " första TextFrame inuti: \"" + (it.textFrames.firstItem().contents || "") + "\"";
                } else {
                    content = " (inga TextFrames inuti — kan inte skrivas på)";
                }
            } catch(e) {
                content = " (kunde inte läsa innehåll: " + e.message + ")";
            }

            rader.push((s + 1) + ". " + namn + " [" + typ + "]" + content);
        }
    }

    if (hittat === 0) {
        rader.push("Inga objekt med namn som börjar med _exemplar_ hittades!");
        rader.push("");
        rader.push("Detta är problemet:");
        rader.push("Markera textframen som ska få S1/S2/S3/S4 och öppna");
        rader.push("Fönster → Användbart → Skriptetikett (Window → Utilities → Script Label)");
        rader.push("Skriv: _exemplar_skede");
        rader.push("");
        rader.push("OBS: namnet ska INTE vara _exemplar_spelare (det är reserverat).");
    } else {
        rader.push("");
        rader.push("Hittade " + hittat + " objekt med _exemplar_-prefix.");
        rader.push("");
        rader.push("För att S1/S2/S3/S4 ska skrivas måste:");
        rader.push("  1. Typen vara 'TextFrame' (eller en grupp som innehåller TextFrames)");
        rader.push("  2. Innehållet vara skrivbart (alltså inte bara en bild eller form)");
    }

    alert(rader.join("\n"));
}

