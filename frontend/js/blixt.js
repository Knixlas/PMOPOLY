// Åkepol Blixt – mässversionen. Ett kvarter, fyra beslut och två tärningsslag.
// All logik körs här i webbläsaren så att spelet tål ett mässnät. Korten (namn, priser,
// effekter) kommer ur speldatan via /api/blixt/kort och sparas lokalt som reserv.

import { skapaDiorama } from "/js/diorama.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const tecken = (v) => (v > 0 ? "+" : v < 0 ? "−" : "±") + Math.abs(v);
const mkr = (v) => `${tecken(v)} Mkr`;
const heltal = (v) => String(v).replace("-", "−");
const d20 = () => 1 + Math.floor(Math.random() * 20);
// Kortens förkortningar i klartext för den som aldrig har sett spelet
const klartext = (t) => String(t).replace(/-(?=\d)/g, "−").replace(/\bH\b/g, "hållbarhet").replace(/\bQ\b/g, "kvalitet").replace(/\bmån\b/g, "månad");

const SKEDEN = [
    { namn: "Projektutveckling", c: "var(--pu)", bg: "var(--pu-bg)", nr: 1 },
    { namn: "Planering", c: "var(--pl)", bg: "var(--pl-bg)", nr: 2 },
    { namn: "Genomförande", c: "var(--gf)", bg: "var(--gf-bg)", nr: 2 },
    { namn: "Förvaltning", c: "var(--f)", bg: "var(--f-bg)", nr: 3 },
];
// Husets form på tomtens 4×4 rutor: kompakt fyrkant eller vinklat
const FORM = { s: [5, 6, 9, 10, 13, 14], a: [4, 5, 6, 10, 14, 15] };
const VILA_S = 75;

let K = null, diorama = null, vila = null;
let S = nyttSpel();
function nyttSpel() { return { steg: 0, val: [null, null, null, null], slag: [null, null, null, null], svar: false, rbAnvand: false, rullar: false }; }

// ── Stegen. Texterna är Blixts, kortens namn och siffror fylls i ur K. ──
function steg() {
    const a = K.anbud, r = K.regler;
    return [
        { skede: 0, kort: `Händelsekort ${K.handelse.nr}`, titel: K.handelse.rubrik,
          text: `Ni har tagit projektet ${K.projekt.namn}, ${K.projekt.bta.toLocaleString("sv")} kvm. Nu klagar de kringboende hos kommunen, veckan innan nämnden ska besluta.`,
          alt: [
              { id: "dialog", namn: "Medborgardialog först", salj: `Kostar ${r.dialog_kostnad} Mkr. Ger +${r.dialog_bonus} på tärningsslaget.` },
              { id: "rakt", namn: "Rakt till nämnden", salj: "Gratis. Tärningen får avgöra." },
          ],
          slag: true, ingress: "Nämnden sammanträder. Slå en D20 och se hur protesterna landar.",
          band: [["1–10", K.handelse.effekter["2-10"].text], ["11–19", K.handelse.effekter["11-15"].text], ["20 och över", K.handelse.effekter["20"].text]].map(([s, e]) => [s, klartext(e)]) },
        { skede: 1, kort: "Projektering", titel: "Två skisser från arkitekten",
          text: "Formen på huset styr vad det kostar att bygga och att värma. Vilken skiss går ni vidare med?",
          alt: [
              { id: "s", namn: "Kompakt fyrkant", salj: `Åke Sundvall standard. Ger +${r.standard_h} hållbarhet.` },
              { id: "a", namn: "Vinklat hus med burspråk", salj: `Mer liv i fasaden. Kostar ${r.avsteg_kostnad} Mkr extra.` },
          ] },
        { skede: 1, kort: "Upphandling · mark och stomme", titel: "Två anbud på bordet",
          text: "De första entreprenörerna sätter nivån för resten av bygget. Vilka skriver ni avtal med?",
          alt: [
              { id: "billig", namn: a.billig.namn.join(" och "), salj: `${a.billig.kostnad} Mkr. Billigast på marknaden, av en anledning.` },
              { id: "erfaren", namn: a.erfaren.namn.join(" och "), salj: `${a.erfaren.kostnad} Mkr. Ett lag som har byggt förut.` },
          ] },
        { skede: 2, kort: "Faskort · etablering", titel: K.fas.namn,
          text: `${K.fas.beskrivning} Hur har ni lagt upp arbetet på platsen?`,
          alt: [
              { id: "fika", namn: `${K.kultur.namn} varje vecka`, salj: `Kulturkort. Kostar ${K.kultur.kostnad} Mkr, ger +${K.kultur.bonus} på slaget.` },
              { id: "ingen", namn: "Ingen tid för fika", salj: "Tidplanen är tajt. Tärningen får avgöra." },
          ],
          slag: true, ingress: "Inspektören kliver in genom grinden. Slå en D20 och lägg till er erfarenhet.",
          band: [[`1–${r.fas_granser[0]}`, K.fas.nivaer[0].text], [`${r.fas_granser[0] + 1}–${r.fas_granser[1]}`, K.fas.nivaer[1].text],
                 [`${r.fas_granser[1] + 1}–${r.fas_granser[2]}`, K.fas.nivaer[2].text], [`${r.fas_granser[2] + 1} och över`, K.fas.nivaer[3].text]].map(([s, e]) => [s, klartext(e)]) },
    ];
}

// ── Ställningen räknas alltid om från valen ──
function stallning() {
    const r = K.regler, { val, slag } = S;
    const st = { qKrav: r.q_krav, hKrav: r.h_krav, q: r.q_start, h: r.h_start, res: r.budget, erf: 0, rb: 0, s1: null, s4: null, band1: null, niva4: null };
    if (val[0] === "dialog") st.res -= r.dialog_kostnad;
    if (slag[0] !== null) {
        st.s1 = slag[0] + (val[0] === "dialog" ? r.dialog_bonus : 0);
        st.band1 = st.s1 <= 10 ? 0 : st.s1 <= 19 ? 1 : 2;
        const t = K.handelse.effekter[["2-10", "11-15", "20"][st.band1]].text.toLowerCase();
        const n = Number((t.match(/[+-]?\d+/) || [1])[0]);
        if (t.includes("kvalitetskrav")) st.qKrav += n;
        if (t.includes("hållbarhetskrav")) st.hKrav += n;
        if (t.includes("riskbuffert")) st.rb += n;
    }
    if (val[1] === "s") st.h += r.standard_h;
    if (val[1] === "a") st.res -= r.avsteg_kostnad;
    if (val[2]) { const a = K.anbud[val[2]]; st.res -= a.kostnad; st.q += a.q; st.h += a.h; st.erf += a.erf; }
    if (val[3] === "fika") st.res -= K.kultur.kostnad;
    if (slag[3] !== null) {
        st.s4 = slag[3] + st.erf + (val[3] === "fika" ? K.kultur.bonus : 0);
        st.niva4 = st.s4 <= r.fas_granser[0] ? 0 : st.s4 <= r.fas_granser[1] ? 1 : st.s4 <= r.fas_granser[2] ? 2 : 3;
        const e = K.fas.nivaer[st.niva4];
        st.res += e.mkr; st.q += e.q; st.h += e.h;
    }
    if (S.rbAnvand) st.rb -= 1;
    st.slut = S.steg > 4;
    st.garanti = st.slut && val[2] === "billig" ? -K.garanti.mkr : 0;
    st.saknas = st.slut ? Math.max(0, st.qKrav - st.q) + Math.max(0, st.hKrav - st.h) : 0;
    st.slutRes = st.res - st.garanti - st.saknas * r.saknat_steg;
    return st;
}

// ── Rendering ──
let forra = {};
function render() {
    const st = stallning(), i = S.steg - 1, s = i >= 0 && i < 4 ? steg()[i] : null;
    const aktivt = st.slut ? 3 : s ? s.skede : -1;
    $("skeden").innerHTML = SKEDEN.map((k, n) => `<span class="${n === aktivt ? "nu" : n < aktivt ? "klar" : ""}" style="--c:${k.c};--c-bg:${k.bg}">${k.namn}</span>`).join("");

    const res = st.slut ? st.slutRes : st.res;
    const matare = [
        ["q", "Kvalitet", `Q ${heltal(st.q)}`, st.slut ? (st.q >= st.qKrav ? `Kravet ${st.qKrav} håller` : `Kravet ${st.qKrav} spricker`) : `krav ${st.qKrav}`, st.slut ? (st.q >= st.qKrav ? "ok" : "fel") : ""],
        ["h", "Hållbarhet", `H ${heltal(st.h)}`, st.slut ? (st.h >= st.hKrav ? `Kravet ${st.hKrav} håller` : `Kravet ${st.hKrav} spricker`) : `krav ${st.hKrav}`, st.slut ? (st.h >= st.hKrav ? "ok" : "fel") : ""],
        ["res", "Resultat", mkr(res), "täckningsbidrag", "", res < 0],
        ["erf", "Erfarenhet", tecken(st.erf), "läggs på slaget", ""],
        ["rb", "Riskbuffert", String(Math.max(0, st.rb)), "ett omslag styck", ""],
    ];
    $("matare").innerHTML = matare.map(([id, n, v, u, klass, rod]) =>
        `<div class="mat ${forra[id] !== undefined && forra[id] !== v + u ? "blink" : ""}"><span class="n">${n}</span><span class="v ${rod ? "fel" : ""}">${v}</span><span class="u ${klass}">${u}</span></div>`).join("");
    forra = Object.fromEntries(matare.map(([id, , v, u]) => [id, v + u]));

    // Kvarteret växer fram: volym → bygge → klart
    const lage = st.slut ? "klart" : S.val[2] ? "bygge" : "plan";
    diorama.kvarter({
        rutor: 16, lage, bygg: S.slag[3] !== null ? 0.9 : 0.4,
        projekt: [{ id: "blixt", namn: K.projekt.namn, typ: K.projekt.typ, rutor: K.projekt.rutor, celler: FORM[S.val[1] || "s"] }],
    });

    const p = $("panel");
    if (S.steg === 0) p.innerHTML = vyStart();
    else if (st.slut) p.innerHTML = vySlut(st);
    else if (!S.svar) p.innerHTML = vyVal(s, i);
    else p.innerHTML = vySvar(s, i, st);
    bind(st, i);
    p.scrollTop = 0;
}

const kicker = (s) => `<span class="kicker" style="--c:${SKEDEN[s].c};--c-bg:${SKEDEN[s].bg}">Skede ${SKEDEN[s].nr} · ${SKEDEN[s].namn}</span>`;

function vyStart() {
    return `<span class="kicker" style="--c:var(--burgundy);--c-bg:var(--f-bg)">Tre minuter</span>
        <h1>Bygg ett kvarter i staden Åkepol.</h1>
        <p class="ingress">Fyra beslut och två tärningsslag tar dig från idé till inflyttat hus. Det är samma resa som våra riktiga projekt gör: utveckla, planera, bygga, förvalta.</p>
        <div class="fyll"></div>
        <button class="knapp rod" id="b-borja">Börja bygga</button>`;
}

function vyVal(s, i) {
    return `${kicker(s.skede)}<span class="kort">${esc(s.kort)}</span>
        <h2>${esc(s.titel)}</h2><p class="ingress">${esc(s.text)}</p>
        <div class="fyll"></div>
        <div class="val">${s.alt.map((o) => `<button class="alt" data-val="${o.id}"><b>${esc(o.namn)}</b><span>${esc(o.salj)}</span></button>`).join("")}</div>`;
}

function vySvar(s, i, st) {
    const vald = s.alt.find((o) => o.id === S.val[i]);
    let html = `${kicker(s.skede)}<h2>${esc(vald.namn)}</h2>`;
    const chips = (lista) => `<div class="chips">${lista.filter(Boolean).map(([t, bra]) => `<span class="chip ${bra ? "bra" : ""}">${esc(t)}</span>`).join("")}</div>`;
    if (s.slag) {
        const slagit = S.slag[i] !== null && !S.rullar;
        const traff = i === 0 ? st.band1 : st.niva4;
        if (!slagit && !S.rullar) {
            return html + `<p class="ingress">${esc(s.ingress)}</p>
                <div class="band">${s.band.map(([spann, eff]) => `<div class="rad"><b>${spann}</b><span>${esc(eff)}</span></div>`).join("")}</div>
                <div class="fyll"></div><button class="knapp rod" id="b-sla">Slå tärningen</button>`;
        }
        let summa = "", utfall = "";
        if (slagit && i === 0) {
            summa = S.val[0] === "dialog" ? `${S.slag[0]} + ${K.regler.dialog_bonus} för dialogen = ${st.s1}` : `Slaget blev ${st.s1}`;
            utfall = ["Nämnden skärper kvalitetskravet", "Protesterna rinner ut i sanden", "Grannarna är med. Ni får en riskbuffert"][st.band1];
        } else if (slagit) {
            summa = [String(S.slag[3]), `${tecken(st.erf)} erfarenhet`, S.val[3] === "fika" ? `+${K.kultur.bonus} ${K.kultur.namn.toLowerCase()}` : ""].filter(Boolean).join("  ") + ` = ${st.s4}`;
            utfall = ["Byggstopp", "Godkänt utan anmärkning", "Beröm av inspektören", "Ett föredöme, säger inspektören"][st.niva4] + (K.fas.nivaer[st.niva4].text !== "Ingen effekt" ? `: ${klartext(K.fas.nivaer[st.niva4].text)}` : "");
        }
        html += `<div class="tarning"><span class="d20 ${S.rullar ? "rullar" : ""}" id="d20">${S.rullar ? "…" : S.slag[i]}</span>
            <div><div class="sum">${esc(summa)}</div><div class="utfall">${esc(utfall)}</div></div></div>`;
        if (slagit) {
            html += `<div class="band">${s.band.map(([spann, eff], n) => `<div class="rad ${n === traff ? "traff" : ""}"><b>${spann}</b><span>${esc(eff)}</span></div>`).join("")}</div>
                <div class="fyll"></div>`;
            if (i === 3 && st.rb > 0 && !S.rbAnvand && st.niva4 < 3) html += `<button class="knapp ljus" id="b-om">Använd riskbufferten och slå om</button>`;
            html += `<button class="knapp" id="b-nasta">${S.steg < 4 ? "Vidare" : "Till inflyttningen"}</button>`;
        }
        return html;
    }
    const r = K.regler;
    if (i === 1) {
        html += S.val[1] === "s"
            ? `<p class="text">Få hörn ger mindre fasad att bygga, täta och värma. Standarden finns för att inget projekt ska behöva lära sig det på nytt.</p>` + chips([["Åke Sundvall standard", true], [`+${r.standard_h} hållbarhet`, true]]) + akepedia("skiss")
            : `<p class="text">Varje hörn och burspråk är mer fasad att bygga, täta och värma. Det går att välja, men det är ett avsteg från standarden och det kostar.</p>` + chips([["Projektspecifik anpassning", false], [`−${r.avsteg_kostnad} Mkr`, false]]) + akepedia("skiss");
    } else {
        const a = K.anbud[S.val[2]];
        html += `<p class="citat">”${esc(a.citat)}”</p><p class="text">${S.val[2] === "billig"
            ? "Pengarna syns direkt. Resten märks senare: på tärningsslagen i bygget och vid garantibesiktningen."
            : "Dyrare i dag. Erfarenheten följer med till varje tärningsslag under bygget."}</p>`
            + chips([[`−${a.kostnad} Mkr`, false], a.q && [`${tecken(a.q)} kvalitet`, a.q > 0], a.h && [`${tecken(a.h)} hållbarhet`, a.h > 0], a.erf && [`${tecken(a.erf)} erfarenhet`, a.erf > 0]]);
    }
    return html + `<div class="fyll"></div><button class="knapp" id="b-nasta">Vidare</button>`;
}

// Var i Åkepedia beslutet hör hemma: dokument och nummer
function akepedia(nyckel) {
    const p = K.akepedia?.[nyckel];
    return p ? `<p class="kort">Åkepedia · ${esc(p.dokument)} · ${esc(p.nr)}</p>` : "";
}

function vySlut(st) {
    const r = K.regler, rader = [];
    if (st.garanti) rader.push([`Garantibesiktning: ${K.garanti.namn}`, `−${st.garanti} Mkr`]);
    if (st.saknas) rader.push([`Konsekvenskort för ${st.saknas} saknade kravsteg`, `−${st.saknas * r.saknat_steg} Mkr`]);
    rader.push(["Krav på kvalitet och hållbarhet", st.saknas ? "Spricker" : "Håller"]);
    rader.push(["Resultat för kvarteret", mkr(st.slutRes)]);
    const rubrik = st.saknas ? "Huset står där. Kraven höll inte." : st.slutRes > 0 ? "Inflyttat, godkänt och med vinst." : "Fint hus, dålig affär.";
    const lardom = S.val[2] === "billig"
        ? "Första missen kostar mest: den billiga upphandlingen följde med genom hela bygget, från tärningsslagen till garantibesiktningen."
        : S.val[1] === "a" ? `Burspråken kostade ${r.avsteg_kostnad} Mkr och en hållbarhetspoäng. Avsteg från standarden går att göra, men de är aldrig gratis.`
        : st.niva4 === 0 ? "Byggstoppet blev dyrt. En riskbuffert eller en kultur som tål inspektion hade räckt."
        : "Inga dyra missar. Tidiga beslut med marginal är det som bär ett projekt ända till förvaltningen.";
    return `${kicker(3)}<h2>${rubrik}</h2>
        <div class="band">${rader.map(([t, v]) => `<div class="rad"><span>${esc(t)}</span><b>${esc(v)}</b></div>`).join("")}</div>
        <p class="text">${esc(lardom)}</p>
        <div class="fyll"></div>
        <div class="slutrad"><div class="qr"><img src="/img/blixt-qr.png" alt="QR-kod" onerror="this.replaceWith('Lägg en QR-kod i img/blixt-qr.png')"></div>
        <button class="knapp ljus" id="b-borja" style="flex:1;min-height:84px">Spela igen</button></div>`;
}

function bind(st, i) {
    const klick = (id, fn) => { const el = $(id); if (el) el.onclick = fn; };
    klick("b-borja", () => { S = nyttSpel(); S.steg = 1; render(); });
    document.querySelectorAll(".alt").forEach((el) => (el.onclick = () => { S.val[i] = el.dataset.val; S.svar = true; render(); }));
    const rulla = (om) => {
        S.rullar = true; if (om) S.rbAnvand = true;
        S.slag[i] = d20(); render();
        const el = $("d20"), t = setInterval(() => { if (el.isConnected) el.textContent = d20(); }, 70);
        setTimeout(() => { clearInterval(t); S.rullar = false; render(); }, 850);
    };
    klick("b-sla", () => rulla(false));
    klick("b-om", () => rulla(true));
    klick("b-nasta", () => { S.steg += 1; S.svar = false; render(); });
}

// Vilar skärmen går den tillbaka till start, så att nästa besökare möter en ren skärm
function rorelse() {
    clearTimeout(vila);
    vila = setTimeout(() => { if (S.steg !== 0) { S = nyttSpel(); render(); } }, VILA_S * 1000);
}
["pointerdown", "keydown"].forEach((h) => addEventListener(h, rorelse));

async function start() {
    try {
        const r = await fetch("/api/blixt/kort");
        if (!r.ok) throw new Error(r.status);
        K = await r.json();
        try { localStorage.setItem("blixt-kort", JSON.stringify(K)); } catch {}
    } catch {
        try { K = JSON.parse(localStorage.getItem("blixt-kort")); } catch {}
    }
    if (!K) { $("panel").innerHTML = `<p class="fel">Korten gick inte att hämta. Kontrollera att servern är igång och ladda om.</p>`; return; }
    diorama = skapaDiorama($("diorama"), { spara: new URLSearchParams(location.search).has("bild") });
    window.blixt = { get S() { return S; }, set S(v) { S = v; render(); }, diorama };
    render(); rorelse();
}
start();
