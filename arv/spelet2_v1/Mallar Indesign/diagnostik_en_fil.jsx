// diagnostik_en_fil.jsx – söker både «» och <<>>

function lasaCSVRubriker(csvFil) {
    csvFil.open("r");
    csvFil.encoding = "UTF-8";
    var rad = csvFil.readln();
    csvFil.close();
    var sep = (rad.indexOf(";") > -1) ? ";" : ",";
    var rubriker = rad.split(sep);
    var set = {};
    for (var i = 0; i < rubriker.length; i++) {
        var r = rubriker[i].replace(/^\s+|\s+$/g, "").replace(/^@/, "");
        if (r) set[r] = true;
    }
    return set;
}

function hittaPlatshallare(doc) {
    var funna = {};
    for (var s = 0; s < doc.spreads.length; s++) {
        var items = doc.spreads[s].allPageItems;
        for (var i = 0; i < items.length; i++) {
            if (!(items[i] instanceof TextFrame)) continue;
            var text = "";
            try { text = items[i].contents; } catch(e) { continue; }
            
            // Matcha både «Namn» och <<Namn>>
            var matches = [];
            var m1 = text.match(/«[^»]+»/g);
            var m2 = text.match(/<<[^>]+>>/g);
            if (m1) matches = matches.concat(m1);
            if (m2) matches = matches.concat(m2);
            
            for (var m = 0; m < matches.length; m++) {
                var namn = matches[m]
                    .replace(/^«|»$/g, "")
                    .replace(/^<<|>>$/g, "")
                    .replace(/^@/, "");
                funna[namn] = true;
            }
        }
    }
    return funna;
}

var inddFil = File.openDialog("Välj InDesign-mall (.indd)", "*.indd");
if (!inddFil) { alert("Avbruten."); exit(); }

var csvFil = File.openDialog("Välj datakälla (.csv)", "*.csv");
if (!csvFil) { alert("Avbruten."); exit(); }

var doc = null;
try {
    doc = app.open(inddFil, false);
    var platshallare = hittaPlatshallare(doc);
    var csvKolumner  = lasaCSVRubriker(csvFil);
    doc.close(SaveOptions.NO);

    var saknas = [], extra = [];
    for (var p in platshallare) { if (!csvKolumner[p]) saknas.push(p); }
    for (var k in csvKolumner)  { if (!platshallare[k] && k !== "") extra.push(k); }

    var rapport = inddFil.name + " ← " + csvFil.name + "\n\n";
    if (saknas.length === 0 && extra.length === 0) {
        rapport += "Allt matchar perfekt!";
    } else {
        if (saknas.length > 0) rapport += "SAKNAS i CSV (finns i design):\n  " + saknas.join("\n  ") + "\n\n";
        if (extra.length > 0)  rapport += "EXTRA i CSV (används ej i design):\n  " + extra.join("\n  ");
    }
    alert(rapport);

} catch(e) {
    try { if (doc) doc.close(SaveOptions.NO); } catch(e2) {}
    alert("Fel: " + e.message);
}

