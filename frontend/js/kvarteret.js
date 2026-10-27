// Åkepol – Kvarteret. Digital kortversion utan spelplaner.
// All spellogik ligger på servern (backend/kvarteret.py); här ritas bara läget.

const $ = (id) => document.getElementById(id);
const dec = (s) => String(s ?? "").replace(/(\d)\.(\d)/g, "$1,$2");
const mkr = (v, d = 0) => `${v > 0 ? "+" : ""}${dec(Number(v).toFixed(d))} Mkr`;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v, d = 1) => Number(v).toFixed(d).replace(".", ",");

let ws = null, S = null, session = null, clockOffset = 0;
let draft = {}, draftKey = "", renderedKey = "";

// ── Texter per steg ──

const DELAR = {
    1: { namn: "Före · Projektutveckling", kort: "Del 1" },
    2: { namn: "Under · Planering och genomförande", kort: "Del 2" },
    3: { namn: "Efter · Förvaltning", kort: "Del 3" },
};

const INTRO = {
    intro1: {
        rubrik: "Del 1: Byggrätten",
        text: "Du har fått en markanvisning på 4 000 kvm (16 rutor). Under fem rundor väljer du samtidigt som de andra bolagen vad du gör: tar ett projekt, går på en medborgardialog, bygger en riskbuffert eller köper mer mark. Varje projekt höjer kraven på kvalitet och hållbarhet. Sedan säger nämnden sitt, och det som blir kvar av intäkterna efter mark och utvecklingskostnader blir din byggbudget (ABT).",
        analog: "I brädspelet slår du tärning och går runt Stadsbyggnadskontoret. Var du hamnar avgör om du får ett projekt, ett dialog- eller politikkort eller en riskbuffert. Sedan pusslar du in projektens former på din tomt. Bostäder får läggas i ett övre lager, men bara om de täcker andra projekt helt.",
        bild: "/img/boards/phase1.jpg",
    },
    intro2: {
        rubrik: "Del 2: Bygget",
        text: "Välj en arbetschef. Upphandla sedan organisation och leverantörer i tre omgångar. Billigt sparar pengar nu, men leverantörer på nivå 1–2 ger garantianmärkningar om fem år. Efter varje upphandling kommer en händelse som du löser med D20 plus erfarenhet. Därefter bygger du genom tre faser, där du lägger kompetenser (STA, KOM, SAM, NOG, INN, ABM) mot faskortens krav. Missar du tid, kvalitet eller hållbarhet drar du konsekvenskort.",
        analog: "I brädspelet upphandlar du alla 13 organisationer och leverantörer en i taget och löser ett händelsekort för varje. Bygget går genom alla åtta faserna, och där lägger du dina personal- och leverantörskort fysiskt mot faskortets krav. Varje kort får användas en gång.",
        bild: "/img/boards/phase2.jpg",
    },
    intro3: {
        rubrik: "Del 3: Året",
        text: "Projekten är nu fastigheter. Anställ en fastighetschef och vid behov fastighetsskötare, så att personalen räcker till alla fastigheter. Under fyra kvartal drar du omvärlds- och händelsekort, får in driftnetto och betalar löner. Varje kvartal fattar du beslut: buda på nya fastigheter (du betalar 30 %, resten lånas), energiuppgradera eller sälja till banken. Yielden rör sig och styr värdet.",
        analog: "I brädspelet går du en kvartalsspiral mot mitten och budar högt mot de andra vid bordet. Energiuppgraderingar och personalens specialiseringar gör stor skillnad när händelsekorten slår till.",
        bild: "/img/boards/phase4.jpg",
    },
};

const STEP_TITLE = {
    lobby: "Väntrum", intro1: "Del 1: Byggrätten", pc: "Välj projektchef", p1: "Vad gör ni den här rundan?",
    p1_res: "Rundans utfall", namnd: "Nämndbeslut", slut1: "Skede 1 klart", intro2: "Del 2: Bygget",
    ac: "Välj arbetschef", upph: "Upphandling", upph_res: "Upphandlingens utfall", fas: "Genomförande",
    fas_res: "Fasens utfall", slut2: "Slutbesiktning och garanti", intro3: "Del 3: Året", fc: "Anställ förvaltare",
    kvartal: "Kvartal", kvartal_res: "Marknaden", final: "Slutresultat",
};

const ORG_SLOTS = ["OPERATIVT TEAM", "STÖDFUNKTIONER", "MARKNADSTEAM", "DIGITALISERING"];
const BILDPREFIX = { BRF: "BRF", "FÖRSKOLA": "FÖRSKOLOR", LOKAL: "LOKAL", KONTOR: "KONTOR", "HYRESRÄTT": "Hyresrätt" };
const projImg = (p) => `/img/projects/${encodeURIComponent(`${BILDPREFIX[p.typ] || p.typ} ${p.namn.split(" ").pop()}`)}.jpg`;
const typNamn = (t) => ({ "FÖRSKOLA": "Förskola", "HYRESRÄTT": "Hyresrätt", BRF: "BRF", LOKAL: "Lokal", KONTOR: "Kontor" }[t] || t);

// ── Start och anslutning ──

function toast(msg) {
    const t = $("toast");
    t.textContent = msg; t.style.display = "block";
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.style.display = "none"), 3500);
}

async function api(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Något gick fel");
    return j;
}

function saveSession(s) { try { sessionStorage.setItem("kvarteret", JSON.stringify(s)); } catch {} }
function loadSession() { try { return JSON.parse(sessionStorage.getItem("kvarteret")); } catch { return null; } }

$("btn-create").onclick = async () => {
    try {
        const j = await api("/api/kvarteret/rooms", { name: $("name").value || "Bolag 1" });
        enter(j.code, j.player_id);
    } catch (e) { $("start-err").textContent = e.message; }
};
$("btn-join").onclick = async () => {
    const code = $("code").value.trim().toUpperCase();
    if (code.length !== 4) { $("start-err").textContent = "Koden har fyra bokstäver."; return; }
    try {
        const j = await api(`/api/kvarteret/rooms/${code}/join`, { name: $("name").value || "Bolag" });
        enter(j.code, j.player_id);
    } catch (e) { $("start-err").textContent = e.message; }
};
$("btn-skip").onclick = () => send({ type: "skip" });

function enter(code, pid) {
    session = { code, pid };
    saveSession(session);
    history.replaceState(null, "", `/kvarteret?rum=${code}`);
    $("start").style.display = "none";
    $("game").style.display = "block";
    connect();
}

function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/kvarteret/ws/${session.code}/${session.pid}`);
    ws.onmessage = (ev) => {
        const m = JSON.parse(ev.data);
        if (m.type === "state") { S = m.state; clockOffset = S.now - Date.now() / 1000; render(); }
        if (m.type === "error") toast(m.message);
    };
    ws.onclose = (ev) => {
        if (ev.code === 4004) {
            saveSession(null);
            $("game").style.display = "none"; $("start").style.display = "flex";
            $("start-err").textContent = "Rummet finns inte längre.";
            return;
        }
        setTimeout(connect, 1500);
    };
}

function send(msg) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(msg)); }
function submit(data) { send({ type: "submit", data }); }

// ── Rendering ──

function render() {
    const me = S.me;
    document.body.className = S.del ? `del${S.del}` : "";
    if (["fas", "fas_res", "slut2"].includes(S.step)) document.body.classList.add("genomforande");
    $("h-del").textContent = S.del ? `${DELAR[S.del].kort} · ${DELAR[S.del].namn}` : "Åkepol · Kvarteret";
    let title = STEP_TITLE[S.step] || S.step;
    if (S.step === "p1" || S.step === "p1_res") title += ` (runda ${S.round} av 5)`;
    if (S.step === "upph") title += `: ${S.shared.namn}`;
    if (S.step === "fas") title += `: fas ${S.shared.steg} av 8`;
    if (S.step.startsWith("kvartal")) title = `${title} ${S.round}`;
    $("h-title").textContent = title;
    $("h-code").textContent = `Rum ${S.code}`;
    $("btn-skip").style.display = me?.is_host && (S.kind === "decision" || S.kind === "info") ? "" : "none";

    $("chips").innerHTML = S.players.map((p) => {
        const done = S.kind === "decision" ? p.submitted : S.kind === "info" ? p.ready : false;
        return `<span class="chip ${done ? "done" : ""}"><span class="dot" style="background:${p.color}"></span>${esc(p.name)}${p.is_bot ? " 🤖" : ""}</span>`;
    }).join("");

    // Rita om huvudytan bara när steget eller mitt eget läge ändrats (så att formulär inte nollställs)
    const submitted = S.kind === "decision" ? me?.submitted : S.kind === "info" ? me?.ready : false;
    const key = `${S.step}:${S.round}:${submitted}:${S.step === "lobby" ? S.players.length : ""}`;
    if (key !== draftKey) { draft = {}; }
    if (key !== renderedKey) {
        renderedKey = key; draftKey = key;
        renderMain();
        window.scrollTo({ top: 0 });
    }
    renderAside();
}

function renderMain() {
    const me = S.me;
    const main = $("main");
    if (S.kind === "decision" && me.submitted) {
        main.innerHTML = `<div class="card waiting"><h2>Beslutet är lagt</h2><p>Väntar på de andra bolagen …</p></div>`;
        return;
    }
    const fn = VIEWS[S.step] || (() => `<p>${esc(S.step)}</p>`);
    main.innerHTML = fn(me);
    BIND[S.step]?.(me);
}

function head(kicker, rubrik, text = "") {
    return `<div class="step-head"><div class="kicker">${esc(kicker)}</div><h2>${esc(rubrik)}</h2>${text ? `<p class="lead">${text}</p>` : ""}</div>`;
}

function readyButton(label = "Klar, vidare") {
    return S.me.ready
        ? `<div class="sumbar"><span class="mono">Väntar på de andra …</span></div>`
        : `<div class="sumbar"><span class="mono">Läs igenom och tryck när du är klar.</span><button class="btn primary" id="btn-ready">${label}</button></div>`;
}
function bindReady() { const b = $("btn-ready"); if (b) b.onclick = () => send({ type: "ready" }); }

function revealRows(reveal, extra = () => "") {
    const rows = reveal?.rows || {};
    const ordered = [...S.players].sort((a, b) => (a.id === S.me.id ? -1 : b.id === S.me.id ? 1 : 0));
    return `<div class="reveal">${ordered.map((p) => {
        const lines = rows[p.id] || [];
        return `<div class="pr ${p.id === S.me.id ? "me" : ""}" style="--c:${p.color}">
            <h3><span>${esc(p.name)}${p.id === S.me.id ? " (du)" : ""}</span>${extra(p)}</h3>
            <ul>${lines.map((l) => `<li><span>${esc(dec(l.text))}</span>${l.mkr ? `<span class="amt ${l.mkr > 0 ? "pos" : "neg"}">${mkr(l.mkr, 1)}</span>` : ""}</li>`).join("") || "<li><span>Inget särskilt hände.</span></li>"}</ul>
        </div>`;
    }).join("")}</div>`;
}

function staffCard(c, extra = "") {
    const komp = Object.entries(c.kompetenser || {}).filter(([, v]) => v).map(([k, v]) => `<span class="stat">${k} ${v}</span>`).join("");
    return `<button class="opt" data-id="${esc(c.id)}">
        <div class="top"><span class="typ">${esc(c.roll || "")} · ${esc(c.specialisering || "")}</span></div>
        <h3>${esc(c.namn)}</h3>
        <div class="stats">${komp}${extra}</div>
        <div class="desc">${esc(c.not_text || "")}</div></button>`;
}

function projCard(p, opts = {}) {
    return `<button class="opt ${opts.sel ? "sel" : ""}" data-typ="${esc(p.typ)}" ${opts.disabled ? "disabled" : ""}>
        <img src="${projImg(p)}" alt="" loading="lazy" onerror="this.style.display='none'">
        <div class="top"><span class="typ">${typNamn(p.typ)}</span><span class="typ">${p.rutor} rutor</span></div>
        <h3>${esc(p.namn)}</h3>
        <div class="stats">
            <span class="stat">${p.bta} kvm BTA</span>
            <span class="stat good">Intäkt ${p.anskaffning} Mkr</span>
            <span class="stat bad">Utveckling ${p.kostnad} Mkr</span>
            ${p.q ? `<span class="stat">Q-krav +${p.q}</span>` : ""}${p.h ? `<span class="stat">H-krav +${p.h}</span>` : ""}
            ${p.tid ? `<span class="stat">Tid +${p.tid} mån</span>` : ""}
            ${p.namnd > 1 ? `<span class="stat bad">Nämnd ≥ ${p.namnd}</span>` : ""}
            <span class="stat">Energi ${p.energiklass}</span>
            ${p.typ !== "BRF" ? `<span class="stat">Driftnetto ${fmt(p.driftnetto)}/kv</span>` : `<span class="stat">Säljs efter bygget</span>`}
        </div>
        ${opts.note ? `<div class="desc" style="font-style:normal;color:var(--danger)">${esc(opts.note)}</div>` : ""}
    </button>`;
}

function analogBox(text, bild) {
    return `<div class="analog"><div class="kicker">Så funkar det i brädspelet</div><p>${esc(text)}</p>${bild ? `<img src="${bild}" alt="Spelplanen i brädspelet" onerror="this.remove()">` : ""}</div>`;
}

// ── Vyer per steg ──

const VIEWS = {
    lobby(me) {
        const host = me.is_host;
        return head("Väntrum", `Rum ${S.code}`, "Dela koden med de andra bolagen, så går de in på samma adress och skriver in koden. Spelet har tre delar på cirka 10 minuter var. Alla fattar sina beslut samtidigt på sin egen skärm.")
            + `<div class="card"><h3>Bolag i rummet (${S.players.length} av 6)</h3><ul style="list-style:none;margin-top:8px;display:grid;gap:6px">${S.players.map((p) =>
                `<li class="row"><span class="chip"><span class="dot" style="background:${p.color}"></span>${esc(p.name)}</span>${p.is_host ? '<span class="kicker">värd</span>' : ""}${p.is_bot && host ? `<button class="btn" style="padding:3px 8px" data-rm="${p.id}">Ta bort</button>` : ""}</li>`).join("")}</ul></div>`
            + (host ? `<div class="sumbar"><button class="btn" id="btn-bot" style="color:var(--paper);border-color:rgba(255,255,255,.5)">+ Datorbolag</button><span class="mono">Spelar du ensam? Lägg till datorbolag att tävla mot.</span><button class="btn primary" id="btn-start">Starta spelet</button></div>`
                : `<div class="card waiting">Väntar på att värden startar spelet …</div>`);
    },
    intro1: (me) => introView("intro1", 1),
    intro2: (me) => introView("intro2", 2),
    intro3: (me) => introView("intro3", 3),

    pc(me) {
        return head("Ledning", "Välj din projektchef", "Projektchefen ger riskbuffertar och kompetenser. Med rätt motstånd kan hen avvärja politikkort eller hjälpa till i nämnden.")
            + `<div class="grid">${me.offer.pc.map((c) => staffCard(c,
                `${c.rb ? `<span class="stat good">+${c.rb} riskbuffert</span>` : ""}${c.namnd_bonus ? `<span class="stat good">Nämnd +${c.namnd_bonus}</span>` : ""}${c.handelsemotstand ? `<span class="stat">Motstånd: ${esc(c.handelsemotstand)}</span>` : ""}`)).join("")}</div>`;
    },

    p1(me) {
        const m = S.shared.market;
        const full = me.n_projects >= 9;
        const projekt = Object.values(m).map((p) => {
            const fits = p.rutor <= me.rutor_kvar;
            return projCard(p, { sel: draft.val === "projekt" && draft.typ === p.typ, disabled: !fits || full, note: fits ? "" : "Får inte plats på din mark" });
        }).join("");
        const alt = (val, rubrik, text, stats) => `<button class="opt ${draft.val === val ? "sel" : ""}" data-val="${val}">
            <div class="typ">${rubrik.typ}</div><h3>${rubrik.h}</h3><div class="desc" style="font-style:normal">${text}</div><div class="stats">${stats}</div></button>`;
        return head(`Runda ${S.round} av 5`, "Vad gör ni den här rundan?", "Alla väljer samtidigt. Om två bolag tar samma projekt avgör en D6, och förloraren får nästa projekt i samma hög. Efter varje runda slår alla en D6 för Stadshuset. Den som slår en etta drar ett politikkort och slår D20 på dess skala.")
            + `<h3 style="margin:6px 0 8px">Projektmarknaden: översta kortet i varje hög</h3><div class="grid">${projekt}</div>
               <h3 style="margin:18px 0 8px">Eller …</h3><div class="grid">
               ${alt("dialog", { typ: "Ruta: Dialog", h: "Medborgardialog" }, "Dra ett dialogkort och slå D20 på kortets skala. Det kan sänka dina krav, ge riskbuffertar eller mer mark.", "")}
               ${alt("riskbuffert", { typ: "Ruta: Riskbuffert", h: "Bygg riskbuffert" }, "+1 riskbuffert. Den ger dig ett omslag när en händelse går dåligt under bygget.", `<span class="stat">Du har ${me.rb}</span>`)}
               ${alt("markexpansion", { typ: "Markexpansion", h: "Köp mer mark" }, `Dra en markexpansion (3–5 rutor). Kostar ${5} Mkr, som dras från byggbudgeten.`, `<span class="stat bad">−5 Mkr</span>`)}
               </div>`
            + `<div class="sumbar"><span class="mono" id="p1-sum">${draft.val ? "" : "Välj ett alternativ."}</span><button class="btn primary" id="btn-go" ${draft.val ? "" : "disabled"}>Lägg beslut</button></div>`;
    },

    p1_res: (me) => head(`Runda ${S.round} av 5`, "Så gick rundan") + revealRows(S.reveal) + readyButton(),
    namnd: (me) => head("Stadsbyggnadsnämnden", "Nämndbeslut", "Projekt med nämndkrav över 1 kräver ett D20-slag. Projektchefens nämndbonus läggs till.") + revealRows(S.reveal) + readyButton(),

    slut1(me) {
        const e = me.ekonomi1;
        return head("Skede 1 klart", "Din byggbudget (ABT)")
            + `<div class="card"><div class="kv">
                <span class="k">Intäkt (projektens anskaffning)</span><span class="v pos">${mkr(e.intakt)}</span>
                <span class="k">Mark och tomt</span><span class="v neg">${mkr(-e.mark)}</span>
                <span class="k">Markexpansioner</span><span class="v neg">${mkr(-e.expansion)}</span>
                <span class="k">Utvecklingskostnad (även för tillbakalämnade projekt)</span><span class="v neg">${mkr(-e.utveckling)}</span>
                <span class="k"><b>ABT, din byggbudget</b></span><span class="v"><b>${fmt(e.abt, 0)} Mkr</b></span>
                <span class="k">BTA / BTA-klass</span><span class="v">${me.bta} kvm · ${me.bta_klass}</span>
                <span class="k">BYA / BYA-klass</span><span class="v">${me.bya} kvm · ${me.bya_klass}</span>
                <span class="k">Kvalitetskrav / hållbarhetskrav</span><span class="v">${me.q_krav} / ${me.h_krav}</span>
               </div></div>`
            + `<h3 style="margin:16px 0 8px">Alla bolag</h3><div class="card"><table class="rank"><tr><th>Bolag</th><th>Projekt</th><th>BTA</th><th>ABT</th></tr>${S.players.map((p) =>
                `<tr><td><span class="chip" style="display:inline-flex"><span class="dot" style="background:${p.color}"></span>${esc(p.name)}</span></td><td>${p.n_projects}</td><td>${p.bta}</td><td>${fmt(p.abt, 0)}</td></tr>`).join("")}</table></div>`
            + readyButton("Till del 2");
    },

    ac(me) {
        return head("Ledning", "Välj din arbetschef", "Arbetschefen ger erfarenhet (bonus på D20-slag), kompetenser till faskorten och ibland bonus på kvalitet, hållbarhet eller tid.")
            + `<div class="grid">${me.offer.ac.map((c) => staffCard(c,
                `<span class="stat good">Erfarenhet ${c.erfarenhet || 0}</span>${c.rb ? `<span class="stat good">+${c.rb} riskbuffert</span>` : ""}${c.q_bonus ? `<span class="stat good">Q +${c.q_bonus}</span>` : ""}${c.h_bonus ? `<span class="stat good">H +${c.h_bonus}</span>` : ""}${c.t_bonus ? `<span class="stat good">Tid −${c.t_bonus} mån</span>` : ""}`)).join("")}</div>`;
    },

    upph(me) {
        for (const s of me.offer.slots) if (draft[s.slot] == null) draft[s.slot] = Math.max(s.min, 2);
        return head(`Upphandling ${S.shared.runda} av ${S.shared.av}`, S.shared.namn,
            "Välj nivå för varje post. Högre nivå kostar mer men ger kvalitet, hållbarhet, erfarenhet och kompetenser. Leverantörer på nivå 1–2 ger ett garantikort var vid femårsbesiktningen.")
            + me.offer.slots.map((s) => `<div class="slot"><div class="row" style="justify-content:space-between"><h3>${esc(s.slot.charAt(0) + s.slot.slice(1).toLowerCase())}</h3>${s.min > 1 ? `<span class="stat bad">Projekten kräver nivå ${s.min}+</span>` : ""}</div>
                <div class="levels">${s.levels.map((l) => `<button class="lvl ${draft[s.slot] === l.niva ? "sel" : ""}" data-slot="${esc(s.slot)}" data-niva="${l.niva}" ${l.niva < s.min ? "disabled" : ""}>
                    <b>Nivå ${l.niva} · ${l.kostnad} Mkr</b><span class="nm">${esc(l.namn)}</span>
                    <span class="stats">${l.q ? `<span class="stat ${l.q > 0 ? "good" : "bad"}">Q ${l.q > 0 ? "+" : ""}${l.q}</span>` : ""}${l.h ? `<span class="stat ${l.h > 0 ? "good" : "bad"}">H ${l.h > 0 ? "+" : ""}${l.h}</span>` : ""}${l.t ? `<span class="stat ${l.t < 0 ? "good" : "bad"}">${l.t > 0 ? "+" : ""}${l.t} mån</span>` : ""}${l.erf ? `<span class="stat ${l.erf > 0 ? "good" : "bad"}">Erf ${l.erf > 0 ? "+" : ""}${l.erf}</span>` : ""}${l.niva <= 2 && !ORG_SLOTS.includes(s.slot) ? `<span class="stat bad">Garantirisk</span>` : ""}</span>
                    <span class="stats">${Object.entries(l.komp).filter(([, v]) => v).map(([k, v]) => `<span class="stat">${k} ${v}</span>`).join("")}</span>
                </button>`).join("")}</div></div>`).join("")
            + `<div class="sumbar"><span class="mono" id="upph-sum"></span><button class="btn primary" id="btn-go">Skriv kontrakt</button></div>`;
    },

    upph_res: (me) => head("Upphandling", S.reveal.title || "Utfall", "Kostnaden dras från ABT. Sedan slår du D20 plus samlad erfarenhet på en händelse, och en riskbuffert ger ett omslag om det går riktigt dåligt.")
        + revealRows(S.reveal, (p) => {
            const v = S.reveal.val?.[p.id] || {};
            return `<span class="mono" style="font-size:.72rem">nivåer ${Object.values(v).join("·")}</span>`;
        }) + readyButton(),

    fas(me) {
        const k = S.shared.kort;
        draft.kultur ??= [];
        const komp = kompAfter(me);
        return head(`Fas ${S.shared.steg} av 8 (${S.shared.runda} av 3 i kortversionen)`, k.namn, `${esc(k.beskrivning)} Samma faskort gäller alla bolag. Du betalar med kompetenspoäng för att nå en nivå, och poängen är förbrukade efteråt.`)
            + `<div class="faskort"><div class="row" style="justify-content:space-between"><span class="kicker">Faskort · krav för ${esc(me.offer.kolumn)}</span><span class="kicker">${esc(k.id)}</span></div>
               <div class="nivaer">${me.offer.nivaer.map((n, i) => {
                   const ok = Object.entries(n.krav).every(([kk, v]) => (komp[kk] || 0) >= v);
                   return `<button class="opt ${draft.niva === i ? "sel" : ""}" data-niva="${i}" ${ok ? "" : "disabled"}>
                       <div class="typ">${esc(n.name)}</div>
                       <div class="stats">${Object.entries(n.krav).map(([kk, v]) => `<span class="stat ${(komp[kk] || 0) >= v ? "good" : "bad"}">${kk} ${v}</span>`).join("") || '<span class="stat">Inga krav</span>'}</div>
                       <div><b>${esc(n.effect)}</b></div></button>`;
               }).join("")}</div></div>
               <h3 style="margin:4px 0 6px">Dina kompetenser</h3><div class="komp">${Object.entries(komp).map(([kk, v]) => `<span>${kk} ${v}</span>`).join("")}</div>
               <h3 style="margin:16px 0 6px">Kulturkort till salu: ${S.shared.kulturpris} Mkr styck</h3>
               <div class="grid">${me.offer.kultur.map((c) => `<button class="opt ${draft.kultur.includes(c.id) ? "sel" : ""}" data-kultur="${esc(c.id)}">
                    <div class="typ">Företagskultur</div><h3>${esc(c.namn)}</h3>
                    <div class="stats">${Object.entries(c.kompetenser).filter(([, v]) => v).map(([kk, v]) => `<span class="stat good">${kk} +${v}</span>`).join("")}</div></button>`).join("")}</div>`
            + `<div class="sumbar"><span class="mono">${draft.niva == null ? "Välj nivå på faskortet." : `${me.offer.nivaer[draft.niva].name}${draft.kultur.length ? ` + ${draft.kultur.length} kulturkort (−${draft.kultur.length * S.shared.kulturpris} Mkr)` : ""}`}</span>
               <button class="btn primary" id="btn-go" ${draft.niva == null ? "disabled" : ""}>Bygg fasen</button></div>`;
    },

    fas_res: (me) => head("Genomförande", S.reveal.title || "Utfall")
        + revealRows(S.reveal, (p) => `<span class="mono" style="font-size:.72rem">${esc(S.reveal.val?.[p.id] || "")}</span>`) + readyButton(),

    slut2: (me) => head("Skede 2 klart", "Slutbesiktning, garanti och BRF-försäljning",
        "Varje steg du missar på tid, kvalitet och hållbarhet ger ett konsekvenskort. Vid femårsbesiktningen dras ett garantikort per konsekvenskort och ett per leverantör på nivå 1–2. Det som är kvar av ABT blir ditt täckningsbidrag (TB). BRF:er säljs och vinsten går till eget kapital.")
        + revealRows(S.reveal) + readyButton("Till del 3"),

    fc(me) {
        draft.fs ??= [];
        const fc = me.offer.fc.find((c) => c.id === draft.fc);
        const kap = (fc?.kapacitet || 0) + me.offer.fs.filter((c) => draft.fs.includes(c.id)).reduce((s, c) => s + c.kapacitet, 0);
        const card = (c, sel, attr) => `<button class="opt ${sel ? "sel" : ""}" ${attr}="${esc(c.id)}">
            <div class="typ">${c.roll} · ${esc(c.specialisering)}</div><h3>${esc(c.namn)}</h3>
            <div class="stats"><span class="stat good">Kapacitet ${c.kapacitet}</span><span class="stat bad">Lön ${fmt(c.lon)} Mkr/kv</span></div></button>`;
        return head("Förvaltning", "Anställ fastighetschef och fastighetsskötare",
            `Du äger ${me.props.length} fastigheter. Personalens samlade kapacitet måste räcka till alla. Specialiseringen lindrar vissa händelsekort.`)
            + `<h3 style="margin-bottom:8px">Fastighetschef (välj en)</h3><div class="grid">${me.offer.fc.map((c) => card(c, draft.fc === c.id, "data-fc")).join("")}</div>
               <h3 style="margin:16px 0 8px">Fastighetsskötare (valfritt)</h3><div class="grid">${me.offer.fs.map((c) => card(c, draft.fs.includes(c.id), "data-fs")).join("")}</div>`
            + `<div class="sumbar"><span class="mono">Kapacitet ${kap} / ${me.props.length} fastigheter</span><button class="btn primary" id="btn-go" ${fc && kap >= me.props.length ? "" : "disabled"}>Anställ</button></div>`;
    },

    kvartal(me) {
        const sh = S.shared;
        draft.bud ??= {};
        const info = sh.info?.[me.id] || [];
        const yb = sh.yield_andring?.b, yk = sh.yield_andring?.k;
        return head(`Kvartal ${sh.kvartal} av 4`, `Omvärld: ${sh.omvarld.rubrik}`, esc(sh.omvarld.beskrivning))
            + `<div class="card"><h3>Det här hände i ditt bolag</h3><ul style="list-style:none;display:grid;gap:4px;margin-top:6px">${info.map((l) =>
                `<li class="row" style="justify-content:space-between"><span>${esc(dec(l.text))}</span>${l.mkr ? `<span class="mono ${l.mkr > 0 ? "pos" : "neg"}" style="font-size:.78rem">${mkr(l.mkr, 1)}</span>` : ""}</li>`).join("") || "<li>Lugnt kvartal.</li>"}</ul>
               <div class="kv" style="margin-top:10px"><span class="k">Yield bostäder</span><span class="v">${fmt(sh.yield_b)} %${yb ? ` (${yb > 0 ? "+" : ""}${fmt(yb)})` : ""}</span>
               <span class="k">Yield kommersiellt</span><span class="v">${fmt(sh.yield_k)} %${yk ? ` (${yk > 0 ? "+" : ""}${fmt(yk)})` : ""}</span>
               <span class="k">Eget kapital nu</span><span class="v">${fmt(me.ek)} Mkr</span></div></div>`
            + (sh.market.length ? `<h3 style="margin:16px 0 8px">Marknaden: dolda bud</h3><p class="lead" style="margin-bottom:8px">Lägsta bud är fastighetsvärdet (driftnetto × 4 / yield × energibonus). Du betalar 30 % av budet ur eget kapital, och resten lånas. Den som köper drar ett DD-kort.</p>
                <div class="grid">${sh.market.map((m) => `<div class="opt">
                    <img src="${projImg(m)}" alt="" onerror="this.style.display='none'">
                    <div class="top"><span class="typ">${typNamn(m.typ)}</span><span class="typ">Energi ${m.energiklass}</span></div><h3>${esc(m.namn)}</h3>
                    <div class="stats"><span class="stat">${m.bta} kvm</span><span class="stat good">Driftnetto ${fmt(m.driftnetto)}/kv</span><span class="stat">Värde ${fmt(m.fv, 0)} Mkr</span></div>
                    <input type="number" min="${Math.ceil(m.fv)}" step="1" placeholder="Bud, minst ${Math.ceil(m.fv)} Mkr" data-bud="${esc(m.id)}" value="${draft.bud[m.id] ?? ""}"></div>`).join("")}</div>`
                : `<p class="lead" style="margin-top:14px">Inga nya fastigheter på marknaden i kvartal ${sh.kvartal}.</p>`)
            + `<h3 style="margin:16px 0 8px">Dina fastigheter</h3><div class="grid">${me.offer.props.map((p) => `<div class="opt">
                <div class="top"><span class="typ">${typNamn(p.typ)}</span><span class="typ">Energi ${p.energiklass}</span></div><h3>${esc(p.namn)}</h3>
                <div class="stats"><span class="stat good">DN ${fmt(p.driftnetto)}/kv</span><span class="stat">Värde ${fmt(p.fv, 0)} Mkr</span></div>
                <div class="row">${p.energiklass !== "A" ? `<button class="btn" style="padding:5px 8px" data-upp="${esc(p.id)}">${draft.upp === p.id ? "✓ " : ""}Energi ↑ (−3 Mkr)</button>` : ""}
                <button class="btn" style="padding:5px 8px" data-salj="${esc(p.id)}">${draft.salj === p.id ? "✓ " : ""}Sälj (80 %)</button></div></div>`).join("") || "<p>Du äger inga fastigheter. Buda på marknaden, för du måste äga minst en när året är slut.</p>"}</div>
               <h3 style="margin:16px 0 8px">Anställ fastighetsskötare? Din kapacitet: ${me.kapacitet}</h3><div class="row">${me.offer.fs.map((f) =>
                `<button class="btn" style="padding:6px 10px" data-fsq="${esc(f.id)}">${draft.fs === f.id ? "✓ " : ""}${esc(f.namn)} · kap ${f.kapacitet} · ${fmt(f.lon)} Mkr/kv</button>`).join("")}</div>`
            + `<div class="sumbar"><span class="mono" id="kv-sum"></span><button class="btn primary" id="btn-go">Lägg beslut</button></div>`;
    },

    kvartal_res(me) {
        const bud = Object.values(S.reveal.bud || {});
        return head(`Kvartal ${S.round}`, "Budgivningen avgjord")
            + (bud.length ? `<div class="card" style="margin-bottom:12px"><table class="bids">${bud.map((b) => `<tr><td><b>${esc(b.namn)}</b><br><span class="mono" style="font-size:.7rem">värde ${fmt(b.fv, 0)} Mkr</span></td>
                <td>${b.bud.map((x) => `<span class="chip" style="display:inline-flex;margin:2px"><span class="dot" style="background:${x.color}"></span>${esc(x.name)} ${fmt(x.bud, 0)}</span>`).join("") || "<i>Inga bud, fastigheten går tillbaka till banken</i>"}</td>
                <td style="text-align:right">${b.vinnare ? `🏠 <b>${esc(b.vinnare)}</b>` : ""}</td></tr>`).join("")}</table></div>` : "")
            + revealRows(S.reveal) + readyButton(S.round === 4 ? "Till slutresultatet" : "Nästa kvartal");
    },

    final(me) {
        const r = S.shared.ranking;
        const mine = me.result;
        return head("Slutresultat", `${esc(r[0].name)} vinner Kvarteret!`, "Poäng = (fastighetsvärde × 30 % + 10 % av eget kapital + TB) / BTA × 1 000, multiplicerat med måluppfyllelsen f(n). Där är n antalet missade steg på tid, kvalitet och hållbarhet.")
            + `<div class="card"><table class="rank"><tr><th>Bolag</th><th>FV × 30 %</th><th>EK</th><th>TB</th><th>BTA</th><th>f(n)</th><th>Poäng</th></tr>
               ${r.map((p, i) => `<tr class="${i === 0 ? "winner" : ""}"><td><span class="chip" style="display:inline-flex"><span class="dot" style="background:${p.color}"></span>${esc(p.name)}</span></td>
               <td>${fmt(p.fv_30, 0)}</td><td>${fmt(p.ek, 0)}</td><td>${fmt(p.tb, 0)}</td><td>${p.bta}</td><td>${Math.round(p.f_n * 100)} %</td><td><b>${fmt(p.score)}</b></td></tr>`).join("")}</table></div>`
            + `<div class="grid" style="margin-top:14px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">
               <div class="card"><h3>Dina dyraste missar</h3><ul style="list-style:none;display:grid;gap:6px;margin-top:6px">${mine.lardomar.filter((l) => l.mkr < 0).map((l) =>
                    `<li><span class="kicker">Del ${l.del}</span><br>${esc(dec(l.text))} <span class="mono neg">${mkr(l.mkr, 1)}</span></li>`).join("") || "<li>Inga missar alls. Imponerande!</li>"}</ul></div>
               <div class="card"><h3>Det som gick bäst</h3><ul style="list-style:none;display:grid;gap:6px;margin-top:6px">${mine.basta.filter((l) => l.mkr > 0).map((l) =>
                    `<li><span class="kicker">Del ${l.del}</span><br>${esc(dec(l.text))} <span class="mono pos">${mkr(l.mkr, 1)}</span></li>`).join("") || "<li>—</li>"}</ul></div></div>`
            + `<div class="analog"><div class="kicker">Vill du ha hela spelet?</div><h2 style="color:var(--paper)">Det här var Åkepol på 30 minuter</h2>
               <p>I brädspelet spelar ni runt ett bord i 3–4 timmar. Ni slår tärning runt Stadsbyggnadskontoret, pusslar in projektformer på tomten, upphandlar alla 13 organisationer och leverantörer och bygger genom alla åtta faserna. Sedan budar ni öga mot öga i förvaltningsspiralen. Samma kort och samma ekonomi, men med mycket mer att diskutera.</p>
               <img src="/img/boards/phase3.jpg" alt="" onerror="this.remove()"></div>`;
    },
};

function introView(step, del) {
    const t = INTRO[step];
    return head(DELAR[del].namn, t.rubrik) + `<div class="card"><p>${esc(t.text)}</p></div>` + analogBox(t.analog, t.bild) + readyButton("Kör!");
}

function kompAfter(me) {
    const komp = { ...me.komp };
    for (const c of me.offer.kultur || []) if (draft.kultur?.includes(c.id))
        for (const [k, v] of Object.entries(c.kompetenser)) komp[k] = (komp[k] || 0) + v;
    return komp;
}

function rerender() { renderMain(); }

// ── Händelsebindningar per steg ──

const on = (sel, fn) => document.querySelectorAll(sel).forEach((el) => (el.onclick = () => fn(el)));

const BIND = {
    lobby() {
        const b = $("btn-bot"); if (b) b.onclick = () => send({ type: "add_bot" });
        const s = $("btn-start"); if (s) s.onclick = () => send({ type: "start" });
        on("[data-rm]", (el) => send({ type: "remove_bot", id: el.dataset.rm }));
    },
    intro1: bindReady, intro2: bindReady, intro3: bindReady,
    p1_res: bindReady, namnd: bindReady, slut1: bindReady, upph_res: bindReady, fas_res: bindReady,
    slut2: bindReady, kvartal_res: bindReady,
    pc() { on(".opt", (el) => submit({ id: el.dataset.id })); },
    ac() { on(".opt", (el) => submit({ id: el.dataset.id })); },
    p1(me) {
        on(".opt[data-typ]", (el) => { draft = { val: "projekt", typ: el.dataset.typ }; rerender(); });
        on(".opt[data-val]", (el) => { draft = { val: el.dataset.val }; rerender(); });
        const sum = $("p1-sum");
        if (draft.val === "projekt") sum.textContent = `Du siktar på ${S.shared.market[draft.typ]?.namn}.`;
        else if (draft.val) sum.textContent = { dialog: "Medborgardialog", riskbuffert: "Riskbuffert", markexpansion: "Markexpansion" }[draft.val];
        $("btn-go").onclick = () => submit(draft);
    },
    upph(me) {
        on(".lvl", (el) => { draft[el.dataset.slot] = +el.dataset.niva; rerender(); });
        let cost = 0, q = me.q, h = me.h, erf = me.erf;
        for (const s of me.offer.slots) {
            const l = s.levels.find((x) => x.niva === draft[s.slot]);
            if (l) { cost += l.kostnad; q += l.q; h += l.h; erf += l.erf; }
        }
        $("upph-sum").innerHTML = `Kostnad ${cost} Mkr → ABT kvar ${fmt(me.abt - cost, 0)} Mkr · Q ${q}/${me.q_krav} · H ${h}/${me.h_krav} · Erf ${erf}`;
        $("btn-go").onclick = () => submit({ val: Object.fromEntries(me.offer.slots.map((s) => [s.slot, draft[s.slot]])) });
    },
    fas(me) {
        on(".opt[data-niva]", (el) => { draft.niva = +el.dataset.niva; rerender(); });
        on(".opt[data-kultur]", (el) => {
            const id = el.dataset.kultur;
            draft.kultur = draft.kultur.includes(id) ? draft.kultur.filter((x) => x !== id) : [...draft.kultur, id];
            // En nivå som inte längre går att nå avmarkeras
            if (draft.niva != null) {
                const komp = kompAfter(me);
                if (!Object.entries(me.offer.nivaer[draft.niva].krav).every(([k, v]) => (komp[k] || 0) >= v)) draft.niva = null;
            }
            rerender();
        });
        $("btn-go").onclick = () => submit({ niva: draft.niva, kultur: draft.kultur });
    },
    fc(me) {
        on("[data-fc]", (el) => { draft.fc = el.dataset.fc; rerender(); });
        on("[data-fs]", (el) => {
            const id = el.dataset.fs;
            draft.fs = draft.fs.includes(id) ? draft.fs.filter((x) => x !== id) : [...draft.fs, id];
            rerender();
        });
        $("btn-go").onclick = () => submit({ fc: draft.fc, fs: draft.fs });
    },
    kvartal(me) {
        const upd = () => {
            const tot = Object.values(draft.bud).reduce((s, v) => s + (+v || 0), 0);
            const parts = [];
            if (tot) parts.push(`Bud ${fmt(tot, 0)} Mkr → du betalar ${fmt(tot * 0.3)} av ${fmt(me.ek)} Mkr EK`);
            if (draft.upp) parts.push("1 energiuppgradering");
            if (draft.salj) parts.push("1 försäljning");
            if (draft.fs) parts.push("1 ny skötare");
            $("kv-sum").textContent = parts.join(" · ") || "Inget beslut är också ett beslut.";
        };
        document.querySelectorAll("[data-bud]").forEach((el) => (el.oninput = () => { draft.bud[el.dataset.bud] = el.value; upd(); }));
        const toggle = (key, attr) => on(`[data-${attr}]`, (el) => { draft[key] = draft[key] === el.dataset[attr] ? null : el.dataset[attr]; rerender(); });
        toggle("upp", "upp"); toggle("salj", "salj"); toggle("fs", "fsq");
        upd();
        $("btn-go").onclick = () => {
            const bud = Object.fromEntries(Object.entries(draft.bud).filter(([, v]) => +v > 0).map(([k, v]) => [k, +v]));
            submit({ bud, uppgradera: draft.upp || null, salj: draft.salj || null, fs: draft.fs || null });
        };
    },
};

// ── Sidopanel: mitt bolag ──

function meter(label, val, krav, invert = false) {
    const ok = invert ? val <= krav : val >= krav;
    const pct = Math.max(4, Math.min(100, invert ? (krav / Math.max(val, 1)) * 100 : (val / Math.max(krav, 1)) * 100));
    return `<div class="meter"><div class="lbl"><span>${label}</span><span>${val} / ${krav}${ok ? " ✓" : ""}</span></div><div class="track"><div class="fill ${ok ? "" : "short"}" style="width:${pct}%"></div></div></div>`;
}

function renderAside() {
    const me = S.me;
    if (!me || S.step === "lobby") { $("aside").innerHTML = ""; return; }
    let html = `<div class="card"><div class="row"><span class="chip"><span class="dot" style="background:${me.color}"></span>${esc(me.name)}</span></div>`;
    if (S.del === 1) {
        const used = me.rutor - me.rutor_kvar;
        html += `<h3>Din mark</h3><div class="tomt">${Array.from({ length: me.rutor }, (_, i) => `<div class="${i < used ? "used" : ""} ${i >= 16 ? "exp" : ""}"></div>`).join("")}</div>
            <div class="kv"><span class="k">Rutor kvar</span><span class="v">${me.rutor_kvar} av ${me.rutor}</span>
            <span class="k">BTA</span><span class="v">${me.bta} kvm (${me.bta_klass})</span>
            <span class="k">Kvalitetskrav</span><span class="v">${me.q_krav}</span><span class="k">Hållbarhetskrav</span><span class="v">${me.h_krav}</span>
            <span class="k">Riskbuffertar</span><span class="v">${me.rb}</span><span class="k">Projektchef</span><span class="v">${esc(me.pc || "–")}</span></div>
            <h3>Projekt</h3><div class="plist">${me.projects.map((p) => esc(p.namn)).join("<br>") || "Inga än"}</div>`;
    } else if (S.del === 2) {
        html += `<div class="kv"><span class="k">ABT kvar</span><span class="v">${fmt(me.abt, 0)} av ${fmt(me.abt_start, 0)} Mkr</span>
            <span class="k">Erfarenhet</span><span class="v">${me.erf}</span><span class="k">Riskbuffertar</span><span class="v">${me.rb}</span>
            <span class="k">Arbetschef</span><span class="v">${esc(me.ac || "–")}</span></div>
            ${meter("Kvalitet", me.q, me.q_krav)}${meter("Hållbarhet", me.h, me.h_krav)}${meter("Tid (mån)", me.t, me.t_mal, true)}
            <h3>Kompetenser</h3><div class="komp" style="margin-top:4px">${Object.entries(me.komp).map(([k, v]) => `<span>${k} ${v}</span>`).join("")}</div>`;
    } else {
        html += `<div class="kv"><span class="k">Eget kapital</span><span class="v ${me.ek < 0 ? "neg" : ""}">${fmt(me.ek)} Mkr</span>
            <span class="k">TB från bygget</span><span class="v">${fmt(me.tb, 0)} Mkr</span>
            <span class="k">Kapacitet</span><span class="v">${me.kapacitet} (${me.props.length} fastigheter)</span>
            <span class="k">Löner</span><span class="v">${fmt(me.lon)} Mkr/kv</span>
            <span class="k">Yield bostäder / kommersiellt</span><span class="v">${fmt(S.yield_b)} / ${fmt(S.yield_k)} %</span>
            <span class="k">Fastighetschef</span><span class="v">${esc(me.fc || "–")}</span></div>
            <h3>Fastigheter</h3><div class="plist">${me.props.map((p) => `${esc(p.namn)} · ${p.energiklass}`).join("<br>") || "Inga"}</div>`;
    }
    html += `</div>`;
    $("aside").innerHTML = html;
}

// ── Klocka ──

setInterval(() => {
    if (!S || !S.deadline) { $("h-clock").textContent = ""; $("h-progress").style.width = progressPct(); return; }
    const left = Math.max(0, Math.round(S.deadline - (Date.now() / 1000 + clockOffset)));
    $("h-clock").textContent = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;
    $("h-clock").classList.toggle("low", left <= 10);
    $("h-progress").style.width = progressPct();
}, 500);

const ORDER = ["intro1", "pc", "p1", "p1_res", "namnd", "slut1", "intro2", "ac", "upph", "upph_res", "fas", "fas_res", "slut2", "intro3", "fc", "kvartal", "kvartal_res", "final"];
function progressPct() {
    if (!S || S.step === "lobby") return "0%";
    const i = ORDER.indexOf(S.step);
    return `${Math.round(((i + 1) / ORDER.length) * 100)}%`;
}

// ── Återanslut om sidan laddas om ──

const saved = loadSession();
const urlRum = new URLSearchParams(location.search).get("rum");
if (saved && (!urlRum || urlRum === saved.code)) enter(saved.code, saved.pid);
else if (urlRum) $("code").value = urlRum;
