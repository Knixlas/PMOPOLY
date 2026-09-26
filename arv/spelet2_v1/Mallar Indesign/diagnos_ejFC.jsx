// diagnos_ejFC.jsx
// Listar alla _ejFC_*-element i den aktiva .indd-filen och rapporterar:
//  - elementets namn
//  - typ (TextFrame, Group, Polygon, etc.)
//  - om det ligger inuti en _keep_*-grupp (då raderas det INTE)
//  - vilket lager det ligger på + om lagret är låst/dolt
//  - parent-kedjan (för att se hur det är grupperat)

if (app.documents.length === 0) {
    alert("Öppna en .indd-fil först.");
} else {
    var doc = app.activeDocument;
    var rader = ["Diagnostik _ejFC_ för: " + doc.name, ""];
    var hittat = 0;
    var problem = 0;

    function listaParents(it) {
        var k = [];
        var p = it.parent;
        while (p) {
            if (p instanceof Spread || p instanceof Page || p instanceof Document) break;
            var n = "";
            try { n = p.name || ""; } catch(e) {}
            var t = "?";
            try {
                if (p instanceof Group) t = "Group";
                else if (p instanceof TextFrame) t = "TextFrame";
                else t = p.constructor.name;
            } catch(e) {}
            k.push(t + (n ? "(\"" + n + "\")" : "(unnamed)"));
            p = p.parent;
        }
        return k.length === 0 ? "direkt på sidan" : k.join(" -> ");
    }

    function arInutiKeepGrupp(it) {
        var p = it.parent;
        while (p) {
            if (p instanceof Spread || p instanceof Page || p instanceof Document) break;
            var n = "";
            try { n = p.name || ""; } catch(e) {}
            if (n.indexOf("_keep_") === 0) return n;
            p = p.parent;
        }
        return null;
    }

    for (var s = 0; s < doc.spreads.length; s++) {
        var spread = doc.spreads[s];
        var items = spread.allPageItems;
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            var namn = "";
            try { namn = it.name || ""; } catch(e) { continue; }
            if (namn.indexOf("_ejFC_") !== 0) continue;

            hittat++;
            var typ = "okänt";
            try {
                if (it instanceof TextFrame) typ = "TextFrame";
                else if (it instanceof Group) typ = "Group";
                else if (it instanceof Rectangle) typ = "Rectangle";
                else if (it instanceof Oval) typ = "Oval";
                else if (it instanceof Polygon) typ = "Polygon";
                else typ = it.constructor.name;
            } catch(e) {}

            var keepGrupp = arInutiKeepGrupp(it);
            var lagerInfo = "";
            try {
                var l = it.itemLayer;
                lagerInfo = l.name +
                            (l.locked ? " [LÅST]" : "") +
                            (!l.visible ? " [DOLT]" : "");
            } catch(e) { lagerInfo = "?"; }

            var parents = listaParents(it);

            var statusText;
            if (keepGrupp) {
                statusText = "** SKIPPAS (inuti _keep_-grupp: " + keepGrupp + ") **";
                problem++;
            } else {
                statusText = "OK — kommer raderas av farglagg om _mildring_roll är tom";
            }

            rader.push("Sida " + (s + 1) + ": " + namn);
            rader.push("    typ:    " + typ);
            rader.push("    lager:  " + lagerInfo);
            rader.push("    parent: " + parents);
            rader.push("    status: " + statusText);
            rader.push("");
        }
    }

    if (hittat === 0) {
        rader.push("Inga _ejFC_*-element hittades i dokumentet.");
        rader.push("");
        rader.push("Detta är problemet om du förväntar dig att vissa element ska");
        rader.push("raderas på F_händelsekort. Markera elementet och sätt namnet");
        rader.push("till t.ex. _ejFC_mildring i Skriptetikett-panelen.");
    } else {
        rader.push("Hittade " + hittat + " element med _ejFC_-prefix.");
        if (problem > 0) {
            rader.push("");
            rader.push("PROBLEM: " + problem + " element ligger inuti _keep_*-grupp och");
            rader.push("kommer aldrig raderas av farglagg-skriptet.");
            rader.push("");
            rader.push("Lösning: avgruppera dem ur _keep_-gruppen, eller ändra");
            rader.push("gruppens namn så det INTE börjar med _keep_.");
        }
    }

    alert(rader.join("\n"));
}

