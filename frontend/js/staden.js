// Åkepol Staden – den långa versionen. Kartan, ställningen och dragen mellan omgångarna.
// Reglerna ligger på servern (backend/staden.py). Själva kvarteren spelas på /kvarteret
// eller /kampanj; hit kommer man tillbaka när partiet är slut.

import { skapaDiorama } from "/js/diorama.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const tal = (v, d = 0) => Number(v).toFixed(d).replace(".", ",");

let session = null, V = null, diorama = null, senast = "";

function toast(msg) {
    const t = $("toast"); t.textContent = msg; t.style.display = "block";
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.style.display = "none"), 3500);
}
async function api(path, body) {
    const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : undefined);
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Något gick fel");
    return j;
}
const spara = (s) => { try { localStorage.setItem("akepol-staden", JSON.stringify(s)); } catch {} };
const las = () => { try { return JSON.parse(localStorage.getItem("akepol-staden")); } catch { return null; } };

// ── Start ──
$("b-skapa").onclick = async () => {
    try {
        const j = await api("/api/staden", { namn: $("namn").value || "Bolag 1", datorbolag: +$("datorbolag").value, langd: $("langd").value });
        in_i(j.kod, j.nyckel);
    } catch (e) { $("start-fel").textContent = e.message; }
};
$("b-ga-med").onclick = async () => {
    const kod = $("kod").value.trim().toUpperCase();
    if (kod.length !== 4) { $("start-fel").textContent = "Koden har fyra bokstäver."; return; }
    try {
        const j = await api(`/api/staden/${kod}/ga-med`, { namn: $("namn").value || "Bolag" });
        in_i(j.kod, j.nyckel);
    } catch (e) { $("start-fel").textContent = e.message; }
};

function in_i(kod, nyckel) {
    session = { kod, nyckel }; spara(session);
    history.replaceState(null, "", `/staden?stad=${kod}`);
    $("start").style.display = "none"; $("spel").style.display = "flex";
    if (!diorama) {
        diorama = skapaDiorama($("karta"), { natt: true, svaj: false });
        diorama.vidVal((id) => drag({ typ: "valj", kvarter: id }));
    }
    hamta(); clearInterval(in_i._t); in_i._t = setInterval(hamta, 2500);
}

async function hamta() {
    try {
        V = await api(`/api/staden/${session.kod}?nyckel=${session.nyckel}`);
        if (!V.jag) throw new Error("Bolaget finns inte i staden.");
    } catch (e) {
        if (!V) { clearInterval(in_i._t); spara(null); $("spel").style.display = "none"; $("start").style.display = "flex"; $("start-fel").textContent = e.message; }
        return;
    }
    const nu = JSON.stringify(V);
    if (nu !== senast) { senast = nu; rita(); }
}

async function drag(body) {
    try { V = await api(`/api/staden/${session.kod}/drag`, { ...body, nyckel: session.nyckel }); senast = JSON.stringify(V); rita(); }
    catch (e) { toast(e.message); }
}

// ── Rita ──
function rita() {
    const jag = V.jag, nasta = V.omgang + 1;
    $("h-kod").textContent = `Stad ${V.kod}`;
    $("nyckeltal").innerHTML = [
        ["Omgång", V.klar ? "Klar" : `${Math.min(nasta, V.omgangar)} av ${V.omgangar}`],
        ["Kassa", `${tal(jag.ek)} Mkr`], ["Fastigheter", jag.fastigheter],
        ["Yield bostäder", `${tal(V.yield_b, 1)} %`], ["Yield kommersiellt", `${tal(V.yield_k, 1)} %`],
    ].map(([k, v]) => `<div><span class="kicker">${k}</span><b>${v}</b></div>`).join("");

    // Kartan
    const ljus = "background:#FAF6EC;color:#1A1410;box-shadow:0 1px 5px rgba(0,0,0,.5)";
    const mork = "background:rgba(20,16,13,.82);color:#E6D9BD;border:1px solid #6B6056";
    diorama.stad({
        kolumner: V.kolumner,
        platser: V.platser.map((p) => {
            if (p.sort !== "kvarter") return p;
            const min = p.agare === jag.namn, valdAvMig = jag.val === p.id;
            let skylt = null, skyltStil = mork;
            if (p.status === "ledig") {
                skylt = valdAvMig ? `${p.namn} · ditt val` : p.vald_av ? `${p.namn} · ${p.agare}` : p.namn;
                if (valdAvMig) skyltStil = "background:#DDA063;color:#1A1410";
            } else if (min || p.status === "pagar") { skylt = p.status === "pagar" ? `${p.namn} · byggs` : p.namn; if (min) skyltStil = ljus; }
            return { ...p, skylt, skyltStil, vald: valdAvMig || !!p.vald_av, bygg: 0.5 };
        }),
    });

    // Vänster: mitt bolag och kunskapsträdet
    const grenar = Object.entries(V.kunskap).map(([id, g]) => {
        const niva = jag.kunskap_niva[id], pris = (niva + 1) * V.kunskap_pris, full = niva >= V.kunskap_max;
        return `<div class="kortet gren"><h3>${esc(g.namn)}<span class="prickar" aria-label="Nivå ${niva} av ${V.kunskap_max}">${Array.from({ length: V.kunskap_max }, (_, i) => `<i class="${i < niva ? "pa" : ""}"></i>`).join("")}</span></h3>
            <small>${esc(g.ger)} per nivå</small>
            <button class="btn" data-gren="${id}" ${full || V.pagar || jag.lardomar < pris ? "disabled" : ""}>${full ? "Full" : `${pris} lärd.`}</button></div>`;
    }).join("");
    $("vanster").innerHTML = `<span class="kicker">Ditt bolag</span>
        <div class="kortet"><h3><span class="prick" style="background:${jag.farg}"></span>${esc(jag.namn)}</h3>
            <div class="kv"><span>Poäng</span><span class="v">${tal(jag.poang)}</span><span>Kvarter klara</span><span class="v">${jag.kvarter}</span>
            <span>Kassa</span><span class="v">${tal(jag.ek)} Mkr</span><span>Fastigheter</span><span class="v">${jag.fastigheter}</span></div></div>
        ${jag.props.length ? `<div class="kortet"><span class="kicker">Bestånd</span>${jag.props.map((p) => `<div class="kv"><span>${esc(p.namn)}</span><span class="v">${p.energiklass} · DN ${p.bas_dn}</span></div>`).join("")}</div>` : ""}
        <span class="kicker" style="margin-top:8px">Kunskapsträdet · ${jag.lardomar} lärdomar</span>
        <p style="font-size:.86rem;color:var(--dov)">Varje färdigt kvarter ger lärdomar. En nivå gäller i alla dina kommande kvarter.</p>
        ${grenar}`;
    document.querySelectorAll("[data-gren]").forEach((el) => (el.onclick = () => drag({ typ: "kunskap", gren: el.dataset.gren })));

    // Höger: ställning och logg
    $("hoger").innerHTML = `<span class="kicker">Ställningen</span>
        <table><tr><th>Bolag</th><th title="Utveckling">Utv.</th><th title="Byggande">Bygg.</th><th title="Förvaltning">Förv.</th><th>Summa</th></tr>
        ${V.stallning.map((b) => `<tr class="${b.id === jag.id ? "jag" : ""}"><td><span class="prick" style="background:${b.farg}"></span>${esc(b.namn)}${!V.pagar && !V.klar && !b.is_bot ? (b.har_valt ? " ✓" : "") : ""}</td>
            <td>${tal(b.s1)}</td><td>${tal(b.s2)}</td><td>${tal(b.s3)}</td><td><b>${tal(b.poang)}</b></td></tr>`).join("")}</table>
        <p style="font-size:.82rem;color:var(--dov)">Utveckling växer för varje kvarter. Byggande är snittet över bolagets kvarter. Förvaltning är bolagets samlade värde just nu.</p>
        <span class="kicker" style="margin-top:8px">Stadens logg</span>
        <div class="logg">${[...V.handelser].reverse().map((h) => `<div>${esc(h.text)}</div>`).join("")}</div>`;

    // Foten: vad som händer nu
    const fot = $("fot");
    if (V.klar) {
        const v = V.stallning[0];
        fot.innerHTML = `<div class="text"><b>Staden är färdigbyggd.</b> ${v.id === jag.id ? "Ditt bolag vinner" : `${esc(v.namn)} vinner`} med ${tal(v.poang)} poäng.</div><button class="btn" id="b-ny">Grunda en ny stad</button>`;
        $("b-ny").onclick = () => { spara(null); location.href = "/staden"; };
    } else if (V.pagar) {
        const r = jag.rum;
        fot.innerHTML = `<div class="text"><b>Omgång ${nasta} pågår.</b> Bolagen bygger sina kvarter. Resultatet förs hit när partiet är slut.</div>
            <a class="btn primar" href="${r.sida}?rum=${r.kod}&pid=${r.pid}">Gå till ditt kvarter</a>`;
    } else {
        const valt = V.platser.find((p) => p.id === jag.val);
        const vantar = V.stallning.filter((b) => !b.is_bot && !b.har_valt).length;
        fot.innerHTML = `<div class="text">${valt ? `<b>Du har valt ${esc(valt.namn)}</b> i stadsdel ${esc(valt.stadsdel)}. ` : "<b>Välj ett ledigt kvarter</b> genom att klicka på det på kartan. "}${jag.vard ? (vantar ? `${vantar} bolag har inte valt än. De får ett ledigt kvarter om du startar ändå.` : "Alla har valt.") : "Den som grundade staden startar omgången."}</div>
            ${jag.vard ? `<button class="btn primar" id="b-starta">Starta omgång ${nasta}</button>` : ""}`;
        const b = $("b-starta"); if (b) b.onclick = () => drag({ typ: "starta" });
    }
}

// ── Kom tillbaka till samma stad ──
const sparad = las(), urlStad = new URLSearchParams(location.search).get("stad");
if (sparad && (!urlStad || urlStad === sparad.kod)) in_i(sparad.kod, sparad.nyckel);
else if (urlStad) $("kod").value = urlStad;
