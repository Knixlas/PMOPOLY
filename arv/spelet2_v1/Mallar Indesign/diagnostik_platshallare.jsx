// diagnostik_platshallare.jsx
// Visar vilka platshållare i varje .indd som saknar matchande kolumn i CSV:en

var ROT = "C:\\Users\\niklas.sviden\\OneDrive - Åke Sundvalls Byggnads AB\\SPELET 2\\";

var MAPPAR = {
    "PU_": ROT + "1. Projektutveckling\\",
    "PL_": ROT + "2. Planering\\",
    "GF_": ROT + "3. Genomförande\\",
    "F_":  ROT + "4. Förvaltning\\",
};

var logg = [];
function log(rad) { logg.push(rad); }

function hittaCSV(mapp, basnamn) {
    var kandidater = [
        basnamn,
        basnamn.replace(/_bildsida$/i, ""),
        basnamn.replace(/_textsida$/i, ""),
    ];
    for (var i = 0; i < kandidater.length; i++) {
        var f = new File(mapp.fsName + "\\" + kandidater[i] + ".csv");
        if (f.exists) return f;
    }
    var alla = mapp.getFiles("*.csv");
    var baslower = basnamn.replace(/_bildsida$/i,"").replace(/_textsida$/i,"").toLowerCase();
    for (var i = 0; i < alla.length; i++) {
        if (alla[i].name.replace(/\.csv$/i,"").toLowerCase() === baslower) return alla[i];
    }
    return null;
}

function lasaCSVRubriker(csvFil) {
    csvFil.open("r");
    csvFil.encoding = "UTF-8";
    var rad = csvFil.readln();
    csvFil.close();
    // Hantera både semikolon och komma
    var sep = (rad.indexOf(";") > -1) ? ";" : ",";
    var rubriker = rad.split(sep);
    var set = {};
    for (var i = 0; i < rubriker.length; i++) {
        var r = rubriker[i].replace(/^\s+|\s+$/g, "").replace(/^@/, "");
        set[r] = true;
    }
    return set;
}

function hittaPlatshallare(doc) {
    var funna = {};
    // Sök i alla textramar i alla spreads
    for (var s = 0; s < doc.spreads.length; s++) {
        var items = doc.spreads[s].allPageItems;
        for (var i = 0; i < items.length; i++) {
            if (!(items[i] instanceof TextFrame)) continue;
            var text = "";
            try { text = items[i].contents; } catch(e) { continue; }
            // Hitta alla «platshållare»
            var matches = text.match(/«[^»]+»/g);
            if (matches) {
                for (var m = 0; m < matches.length; m++) {
                    var namn = matches[m].replace(/^«|»$/g, "").replace(/^@/, "");
                    funna[namn] = true;
                }
            }
        }
    }
    return funna;
}

var harProblem = false;

for (var prefix in MAPPAR) {
    var mapp = new Folder(MAPPAR[prefix]);
    if (!mapp.exists) continue;

    var filer = mapp.getFiles(prefix + "*.indd");
    for (var f = 0; f < filer.length; f++) {
        var inddFil = filer[f];
        var basnamn = decodeURIComponent(inddFil.name.replace(/\.indd$/i, ""));
        var csvFil  = hittaCSV(mapp, basnamn);

        if (!csvFil) continue; // Hoppa om ingen CSV alls

        var doc = null;
        try {
            doc = app.open(inddFil, false);
            var platshallare = hittaPlatshallare(doc);
            var csvKolumner  = lasaCSVRubriker(csvFil);

            var saknas = [];
            for (var p in platshallare) {
                if (!csvKolumner[p]) saknas.push(p);
            }

            var extra = [];
            for (var k in csvKolumner) {
                if (!platshallare[k] && k !== "") extra.push(k);
            }

            if (saknas.length > 0 || extra.length > 0) {
                harProblem = true;
                log("\n" + basnamn + " ← " + csvFil.name);
                if (saknas.length > 0) log("  SAKNAS i CSV:  " + saknas.join(", "));
                if (extra.length > 0)  log("  EXTRA i CSV:   " + extra.join(", "));
            } else {
                log(basnamn + " – OK");
            }

            doc.close(SaveOptions.NO);
        } catch(e) {
            log("FEL vid " + basnamn + ": " + e.message);
            try { if (doc) doc.close(SaveOptions.NO); } catch(e2) {}
        }
    }
}

// Skriv loggfil
var loggFil = new File(ROT + "diagnostik_platshallare.txt");
loggFil.open("w");
loggFil.encoding = "UTF-8";
loggFil.write(logg.join("\n"));
loggFil.close();

alert(harProblem 
    ? "Hittade avvikelser!\nSe: " + ROT + "diagnostik_platshallare.txt"
    : "Allt matchar perfekt!\nSe: " + ROT + "diagnostik_platshallare.txt");

