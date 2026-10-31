// tryckeri_88x146.jsx
// Wrapper: producerar tryckeri-PDF:er för kort i storlek 88 × 146 mm.
// Anropar tryckeri_engine.jsx som gör jobbet.

TARGET_W_MM   = 88;
TARGET_H_MM   = 146;
STORLEK_NAMN  = "88x146";

var thisFil   = new File($.fileName);
var engineFil = new File(thisFil.parent.fsName + "/tryckeri_engine.jsx");

if (!engineFil.exists) {
    alert("tryckeri_engine.jsx saknas i samma mapp som detta skript.\n" +
          "Sökväg som söktes: " + engineFil.fsName);
} else {
    app.doScript(engineFil, ScriptLanguage.JAVASCRIPT);
}

