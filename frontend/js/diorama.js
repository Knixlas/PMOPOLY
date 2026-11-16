// Åkepols diorama: kvarteret och staden i 3D.
// Ritar bara det läge den får. All spellogik ligger på servern eller i respektive spel.
//
//   const d = skapaDiorama(behallare);
//   d.kvarter({ rutor: 16, bygg: 0.4, lage: "bygge", projekt: [{ id, namn, typ, rutor }] });
//   d.stad({ kolumner: 6, platser: [{ id, sort: "kvarter", status: "klart", farg: "#E4572E", ... }] });

import * as THREE from "/vendor/three/three.module.min.js";

export const TYPFARG = { BRF: "#2D7A3A", "HYRESRÄTT": "#8A3030", "FÖRSKOLA": "#1A6B9A", LOKAL: "#C87820", KONTOR: "#5B3A8A" };
const BOSTAD = ["BRF", "HYRESRÄTT"];
const VANINGAR = { LOKAL: 1, "FÖRSKOLA": 1, KONTOR: 2, "HYRESRÄTT": 3, BRF: 3 };
const VH = 0.34;           // våningshöjd i rutor
const MARK = "#E6D9BD", GRAS = "#B7CB7A", GRUS = "#CDBE9F", STOMME = "#CFC5BB", KRAN = "#DDA063";

function hash(s) { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return ((h >>> 0) % 1000) / 1000; }

// ── Texturer (ritas en gång) ──

function duk(w, h, rita) {
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    rita(c.getContext("2d"), w, h);
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
    return t;
}
const TEX = {};
function textur(namn) {
    if (TEX[namn]) return TEX[namn];
    if (namn === "fasad" || namn === "fasad-kvall") {
        TEX[namn] = duk(128, 64, (g, w, h) => {
            g.fillStyle = "#FBF6EE"; g.fillRect(0, 0, w, h);
            g.fillStyle = "#E9DFD0"; g.fillRect(0, h - 5, w, 5);
            for (let i = 0; i < 2; i++) {
                const tand = namn === "fasad-kvall" && i === 0;
                g.fillStyle = tand ? "#F2C879" : "#56656E";
                g.fillRect(14 + i * 64, 16, 36, 30);
                g.fillStyle = "rgba(255,255,255,.35)"; g.fillRect(14 + i * 64, 16, 36, 3);
            }
        });
    } else if (namn === "stomme") {
        TEX[namn] = duk(64, 64, (g, w, h) => {
            g.fillStyle = "#3A322C"; g.fillRect(0, 0, w, h);
            g.fillStyle = STOMME; g.fillRect(0, 0, w, 12); g.fillRect(0, h - 4, w, 4);
            g.fillRect(0, 0, 7, h); g.fillRect(w - 7, 0, 7, h);
        });
    } else if (namn === "sockel") {
        TEX[namn] = duk(128, 64, (g, w, h) => {
            g.fillStyle = "#FFFFFF"; g.fillRect(0, 0, w, h);
            g.fillStyle = "rgba(20,16,13,.72)"; g.fillRect(12, 14, 46, 42); g.fillRect(72, 14, 44, 42);
        });
    }
    return TEX[namn];
}

// ── Dioraman ──

export function skapaDiorama(behallare, val = {}) {
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: !!val.spara });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    behallare.style.position ||= "relative";
    renderer.domElement.style.cssText = "width:100%;height:100%;display:block;touch-action:none";
    behallare.appendChild(renderer.domElement);
    const skyltlager = document.createElement("div");
    skyltlager.style.cssText = "position:absolute;inset:0;pointer-events:none;overflow:hidden";
    behallare.appendChild(skyltlager);

    const scen = new THREE.Scene();
    const kamera = new THREE.OrthographicCamera(-1, 1, 1, -1, -100, 200);
    scen.add(new THREE.HemisphereLight(0xfffaf0, 0xcdbfa6, val.natt ? 0.6 : 1.5));
    const sol = new THREE.DirectionalLight(0xfff1dc, val.natt ? 1.2 : 1.9);
    sol.castShadow = true; sol.shadow.mapSize.set(2048, 2048); sol.shadow.bias = -0.0004; sol.shadow.normalBias = 0.02;
    scen.add(sol, sol.target);
    const skugga = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.ShadowMaterial({ opacity: val.natt ? 0.35 : 0.16 }));
    skugga.rotation.x = -Math.PI / 2; skugga.position.y = -0.31; skugga.receiveShadow = true;
    scen.add(skugga);
    const rot = new THREE.Group(); scen.add(rot);

    const delar = new Map();       // nyckel → { mesh, mal }
    let radie = 6, mitt = new THREE.Vector3(), vinkel = Math.PI / 4, vinkelMal = Math.PI / 4, zoom = 1, svaj = val.svaj ?? true;
    let skyltar = [], valbara = [], onValj = null, hovrad = null, kranar = [];

    const enhet = new THREE.BoxGeometry(1, 1, 1); enhet.translate(0, 0.5, 0);
    const matCache = new Map();
    function mat(farg, extra = {}) {
        const k = farg + JSON.stringify(extra);
        if (!matCache.has(k)) matCache.set(k, new THREE.MeshStandardMaterial({ color: farg, roughness: 0.92, metalness: 0, ...extra }));
        return matCache.get(k);
    }
    function texMat(namn, vaningar, farg = "#FFFFFF", bredd = 1) {
        const k = `${namn}:${vaningar}:${farg}:${bredd}`;
        if (!matCache.has(k)) {
            const t = textur(namn).clone(); t.needsUpdate = true; t.repeat.set(bredd, vaningar);
            matCache.set(k, new THREE.MeshStandardMaterial({ map: t, color: farg, roughness: 0.9 }));
        }
        return matCache.get(k);
    }
    const sidor = (sida, tak) => [sida, sida, tak, tak, sida, sida];

    // En del är en låda med nyckel. Finns nyckeln redan flyttas och växer den mjukt till sitt nya mål.
    function lada(nyckel, { x, z, y = 0, b = 1, d = 1, h = 1, material, skuggar = true, direkt = false, data = null }) {
        let del = delar.get(nyckel);
        if (!del) {
            const mesh = new THREE.Mesh(enhet, material);
            mesh.castShadow = skuggar; mesh.receiveShadow = true;
            mesh.position.set(x, y, z); mesh.scale.set(b, direkt ? h : 0.001, d);
            rot.add(mesh);
            del = { mesh, mal: {} };
            delar.set(nyckel, del);
        }
        del.mesh.material = material;
        del.mesh.userData = data || {};
        del.mal = { x, y, z, b, d, h };
        del.kvar = true;
        return del.mesh;
    }

    function borja() { for (const d of delar.values()) d.kvar = false; skyltar = []; valbara = []; kranar = []; }
    function sluta() {
        for (const [k, d] of delar) if (!d.kvar) { d.mal = { ...d.mal, h: 0.001 }; d.bort = true; }
        skyltlager.innerHTML = "";
        for (const s of skyltar) {
            const el = document.createElement("div");
            el.textContent = s.text;
            el.style.cssText = "position:absolute;transform:translate(-50%,-100%);white-space:nowrap;font:700 12px/1.2 'DM Sans',system-ui,sans-serif;padding:3px 8px;border-radius:5px;" + (s.stil || "background:#FAF6EC;color:#1A1410;box-shadow:0 1px 4px rgba(0,0,0,.25)");
            skyltlager.appendChild(el); s.el = el;
        }
    }

    function kran(nyckel, x, z, hojd) {
        const m = mat(KRAN);
        lada(nyckel + ":mast", { x, z, b: 0.07, d: 0.07, h: hojd, material: m });
        const arm = lada(nyckel + ":arm", { x, z, y: hojd, b: 1.9, d: 0.05, h: 0.05, material: m });
        arm.userData.kran = true; kranar.push(arm);
        lada(nyckel + ":hytt", { x, z, y: hojd - 0.16, b: 0.16, d: 0.16, h: 0.16, material: m });
    }
    function trad(nyckel, x, z, s = 1) {
        lada(nyckel + ":stam", { x, z, b: 0.06 * s, d: 0.06 * s, h: 0.16 * s, material: mat("#8A6A45") });
        lada(nyckel + ":krona", { x, z, y: 0.16 * s, b: 0.3 * s, d: 0.3 * s, h: 0.3 * s, material: mat("#7C9A3A") });
        lada(nyckel + ":topp", { x, z, y: 0.46 * s, b: 0.18 * s, d: 0.18 * s, h: 0.16 * s, material: mat("#8FAA4A") });
    }

    // ── Kvarteret: tomten med sina projekt ──
    // lage: "plan" (genomskinliga volymer), "bygge" (stomme, kran, bygg 0–1), "klart"
    function kvarter(m) {
        borja();
        const rutor = Math.max(16, m.rutor || 16), kol = 4, rader = Math.ceil(rutor / kol);
        const x0 = -(kol - 1) / 2, z0 = -(rader - 1) / 2;
        const plats = (i) => ({ x: x0 + (i % kol), z: z0 + Math.floor(i / kol) });
        lada("mark", { x: 0, z: 0, y: -0.3, b: kol + 0.5, d: rader + 0.5, h: 0.3, material: mat(MARK), direkt: true });

        // Bostäder får ligga i ett övre lager ovanpå andra projekt (staplingsregeln).
        // Ett projekt med egna celler (t.ex. Blixts husform) placeras där, övriga fyller på i tur och ordning.
        const ovr = new Array(rutor).fill(null), bost = new Array(rutor).fill(null);
        const lager = (p) => (BOSTAD.includes(p.typ) ? bost : ovr);
        for (const p of m.projekt || []) for (const c of p.celler || []) if (c < rutor) lager(p)[c] = p;
        for (const p of m.projekt || []) {
            if (p.celler) continue;
            const l = lager(p);
            for (let k = 0, i = 0; k < p.rutor && i < rutor; i++) if (!l[i]) { l[i] = p; k++; }
        }
        const lage = m.lage || "plan", bygg = lage === "klart" ? 1 : Math.max(0, Math.min(1, m.bygg ?? 0));
        const kvall = !!m.kvall;
        let hogst = 0;
        for (let i = 0; i < rutor; i++) {
            const { x, z } = plats(i), nedre = ovr[i], ovre = bost[i];
            const bebyggd = nedre || ovre;
            lada("ruta" + i, { x, z, y: 0, b: 0.96, d: 0.96, h: 0.02, material: mat(bebyggd ? GRUS : (i >= 16 ? "#D9C9A8" : GRAS)), skuggar: false, direkt: true });
            if (!bebyggd) {
                if (lage === "klart" && hash("t" + i) > 0.35) trad("trad" + i, x + (hash("x" + i) - 0.5) * 0.4, z + (hash("z" + i) - 0.5) * 0.4, 0.9 + hash("s" + i) * 0.5);
                continue;
            }
            let y = 0.02;
            for (const [p, niva] of [[nedre, "n"], [ovre, "o"]]) {
                if (!p) continue;
                const van = VANINGAR[p.typ] + (hash(p.id) > 0.6 && BOSTAD.includes(p.typ) ? 1 : 0);
                const full = van * VH;
                const farg = TYPFARG[p.typ] || "#6B6056";
                const nyckel = `hus${i}${niva}`;
                if (lage === "plan") {
                    // Volymstudie: ljus modell med projekttypens färg på taket
                    lada(nyckel, { x, z, y, b: 0.88, d: 0.88, h: full, material: sidor(mat("#F6EFE0"), mat(farg)) });
                } else {
                    // Bygget reser sig nerifrån: den nedre volymen först, sedan den övre
                    const start = niva === "n" ? 0 : (nedre ? 0.35 : 0), slut = niva === "n" ? (ovre ? 0.45 : 1) : 1;
                    const andel = lage === "klart" ? 1 : Math.max(0, Math.min(1, (bygg - start) / (slut - start)));
                    const klar = lage === "klart" || (andel >= 1 && bygg >= 0.92);
                    const h = Math.max(0.001, full * andel);
                    const sida = klar ? texMat(niva === "n" && !BOSTAD.includes(p.typ) ? "sockel" : (kvall ? "fasad-kvall" : "fasad"), van, niva === "n" && !BOSTAD.includes(p.typ) ? farg : "#FFFFFF")
                                      : texMat("stomme", Math.max(1, Math.round(van * andel)));
                    if (andel > 0) lada(nyckel, { x, z, y, b: 0.88, d: 0.88, h, material: sidor(sida, mat(klar ? farg : STOMME)), data: { projekt: p.id } });
                }
                y += full;
            }
            hogst = Math.max(hogst, y);
        }
        if (lage === "bygge" && bygg < 0.98) kran("kran", x0 + 1.5, z0 + Math.min(rader - 1, 1.5), hogst + 1.3);
        const kopta = (m.kopta || []).slice(0, 2 * rader + 2);
        for (const [i, k] of kopta.entries()) {
            // Fastigheter utanför tomten (köpta, eller från tidigare kvarter) står längs kanten
            const x = x0 - 1.3 - Math.floor(i / (rader + 1)) * 0.9, z = z0 + (i % (rader + 1)) * 0.9;
            lada("kopt" + i, { x, z, y: -0.3, b: 0.8, d: 0.8, h: 0.3 + 0.02, material: mat(MARK), direkt: true });
            lada("kopthus" + i, { x, z, y: 0.02, b: 0.64, d: 0.64, h: (VANINGAR[k.typ] || 2) * VH, material: sidor(texMat(kvall ? "fasad-kvall" : "fasad", VANINGAR[k.typ] || 2), mat(TYPFARG[k.typ] || "#6B6056")) });
        }
        mitt.set(0, hogst * 0.3, 0);
        radie = Math.max(kol, rader) * 0.66 + hogst * 0.42 + ((m.kopta || []).length ? 0.6 : 0);
        sluta();
    }

    // ── Staden: kvarter, park, vatten och gammal stad på ett rutnät ──
    function stad(m) {
        borja();
        const kol = m.kolumner || 6, platser = m.platser || [], rader = Math.ceil(platser.length / kol), steg = 1.35;
        const x0 = -((kol - 1) * steg) / 2, z0 = -((rader - 1) * steg) / 2;
        const bas = val.natt ? "#2A231D" : "#D9C9A8", kvartersmark = val.natt ? "#463D35" : MARK;
        lada("brade", { x: 0, z: 0, y: -0.3, b: kol * steg + 0.5, d: rader * steg + 0.5, h: 0.3, material: mat(bas), direkt: true });
        let hogst = 1;
        platser.forEach((p, i) => {
            const x = x0 + (i % kol) * steg, z = z0 + Math.floor(i / kol) * steg, k = "p" + (p.id ?? i);
            if (p.sort === "vatten") {
                lada(k, { x, z, y: 0, b: steg, d: steg, h: 0.015, material: mat(val.natt ? "#2F4D59" : "#8DB9C4"), skuggar: false, direkt: true });
                return;
            }
            if (p.sort === "park") {
                lada(k, { x, z, y: 0, b: 1.1, d: 1.1, h: 0.03, material: mat(val.natt ? "#4F6B1F" : GRAS), skuggar: false, direkt: true });
                for (let t = 0; t < 4; t++) trad(k + "t" + t, x + (hash(k + "x" + t) - 0.5) * 0.8, z + (hash(k + "z" + t) - 0.5) * 0.8, 1 + hash(k + t) * 0.6);
                return;
            }
            lada(k, { x, z, y: 0, b: 1.1, d: 1.1, h: 0.03, material: mat(kvartersmark), skuggar: false, direkt: true });
            if (p.sort === "stad") {
                for (let t = 0; t < 4; t++) {
                    if (hash(k + "s" + t) < 0.15) continue;
                    const h = 0.25 + hash(k + "h" + t) * (p.hog ? 1.1 : 0.6);
                    lada(k + "h" + t, { x: x + (t % 2 ? 0.27 : -0.27), z: z + (t > 1 ? 0.27 : -0.27), y: 0.03, b: 0.46, d: 0.46, h, material: mat(val.natt ? (hash(k + t) > 0.5 ? "#857A70" : "#776D64") : (hash(k + t) > 0.5 ? "#D6C8AE" : "#C9BBA0")) });
                }
                return;
            }
            // Kvarter
            const farg = p.farg || "#6B6056", data = { kvarter: p.id };
            if (p.status === "ledig") {
                const ram = mat(KRAN);
                for (const [dx, dz, b, d] of [[0, -0.5, 1.04, 0.04], [0, 0.5, 1.04, 0.04], [-0.5, 0, 0.04, 1.04], [0.5, 0, 0.04, 1.04]])
                    lada(k + "ram" + dx + dz, { x: x + dx, z: z + dz, y: 0.03, b, d, h: 0.05, material: ram, skuggar: false, data });
                const yta = lada(k + "yta", { x, z, y: 0.03, b: 1.0, d: 1.0, h: 0.012, material: mat(KRAN, { transparent: true, opacity: p.vald ? 0.6 : 0.22 }), skuggar: false, data });
                valbara.push(yta);
            } else {
                const h = p.status === "pagar" ? 0.3 + 0.6 * (p.bygg ?? 0.4) : 0.6 + Math.min(1.2, (p.hojd ?? 0.5) * 1.2);
                const sida = p.status === "pagar" ? texMat("stomme", 2) : texMat(val.natt ? "fasad-kvall" : "fasad", Math.max(2, Math.round(h / VH)), "#FFFFFF", 2);
                const tak = mat(p.status === "pagar" ? STOMME : farg);
                lada(k + "a", { x: x - 0.02, z: z - 0.28, y: 0.03, b: 0.96, d: 0.4, h, material: sidor(sida, tak), data });
                lada(k + "b", { x: x - 0.3, z: z + 0.2, y: 0.03, b: 0.4, d: 0.56, h: h * 0.8, material: sidor(sida, tak), data });
                lada(k + "gard", { x: x + 0.2, z: z + 0.2, y: 0.03, b: 0.56, d: 0.56, h: 0.02, material: mat(val.natt ? "#6F8F35" : GRAS), skuggar: false, direkt: true });
                lada(k + "flagga", { x: x + 0.42, z: z + 0.42, y: 0.03, b: 0.14, d: 0.14, h: 0.14, material: mat(farg) });
                if (p.status === "pagar") kran(k + "kran", x + 0.25, z + 0.2, h + 0.9);
                hogst = Math.max(hogst, h);
                p._h = h + (p.status === "pagar" ? 0.9 : 0);
            }
            if (p.skylt) skyltar.push({ text: p.skylt, x, y: (p.status === "ledig" ? 0.3 : p._h + 0.35), z, stil: p.skyltStil });
        });
        mitt.set(0, 0.3, 0);
        radie = Math.max(kol, rader) * steg * 0.5 + 0.9;
        sluta();
    }

    // ── Kamera, storlek, pekare ──
    function storlek() {
        const w = behallare.clientWidth || 1, h = behallare.clientHeight || 1;
        renderer.setSize(w, h, false);
        const s = radie / zoom, kvot = w / h;
        if (kvot >= 1) { kamera.left = -s * kvot; kamera.right = s * kvot; kamera.top = s; kamera.bottom = -s; }
        else { kamera.left = -s; kamera.right = s; kamera.top = s / kvot; kamera.bottom = -s / kvot; }
        kamera.updateProjectionMatrix();
    }
    const obs = new ResizeObserver(storlek); obs.observe(behallare);

    let drar = null;
    const dom = renderer.domElement;
    dom.addEventListener("pointerdown", (e) => { drar = { x: e.clientX, v: vinkelMal, flyttat: false }; dom.setPointerCapture(e.pointerId); });
    dom.addEventListener("pointermove", (e) => {
        if (drar) { const dx = e.clientX - drar.x; if (Math.abs(dx) > 4) drar.flyttat = true; vinkelMal = drar.v - dx * 0.008; return; }
        if (!valbara.length) return;
        const tr = traff(e); hovrad = tr; dom.style.cursor = tr ? "pointer" : "";
    });
    dom.addEventListener("pointerup", (e) => {
        const d = drar; drar = null;
        if (d && !d.flyttat && onValj) { const tr = traff(e); if (tr) onValj(tr.userData.kvarter); }
    });
    const stralar = new THREE.Raycaster();
    function traff(e) {
        const r = dom.getBoundingClientRect();
        stralar.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), kamera);
        return stralar.intersectObjects(valbara, false)[0]?.object || null;
    }

    const klocka = new THREE.Clock();
    let igang = true, v = new THREE.Vector3();
    function bild() {
        if (!igang) return;
        const dt = Math.min(0.05, klocka.getDelta()), t = klocka.elapsedTime, k = 1 - Math.exp(-dt * 6);
        for (const [nyckel, d] of delar) {
            const m = d.mesh, mal = d.mal;
            m.position.x += (mal.x - m.position.x) * k; m.position.z += (mal.z - m.position.z) * k; m.position.y += (mal.y - m.position.y) * k;
            m.scale.x += (mal.b - m.scale.x) * k; m.scale.z += (mal.d - m.scale.z) * k; m.scale.y += (mal.h - m.scale.y) * k;
            if (d.bort && m.scale.y < 0.01) { rot.remove(m); delar.delete(nyckel); }
        }
        for (const a of kranar) a.rotation.y = Math.sin(t * 0.35) * 0.9;
        vinkel += (vinkelMal - vinkel) * k;
        const a = vinkel + (svaj && !drar ? Math.sin(t * 0.18) * 0.12 : 0), hojd = 0.72;
        kamera.position.set(mitt.x + Math.cos(a) * 30, mitt.y + 30 * hojd, mitt.z + Math.sin(a) * 30);
        kamera.lookAt(mitt);
        sol.position.set(mitt.x + 7, 24, mitt.z + 16); sol.target.position.copy(mitt);
        const sk = sol.shadow.camera, r = radie * 1.6;
        if (sk.right !== r) { sk.left = -r; sk.right = r; sk.top = r; sk.bottom = -r; sk.near = 1; sk.far = 80; sk.updateProjectionMatrix(); storlek(); }
        renderer.render(scen, kamera);
        const w = dom.clientWidth, h = dom.clientHeight;
        for (const s of skyltar) {
            v.set(s.x, s.y, s.z).project(kamera);
            s.el.style.left = `${(v.x * 0.5 + 0.5) * w}px`; s.el.style.top = `${(-v.y * 0.5 + 0.5) * h}px`;
        }
        requestAnimationFrame(bild);
    }
    storlek(); requestAnimationFrame(bild);

    return {
        kvarter, stad, storlek,
        vidVal(fn) { onValj = fn; },
        zoom(z) { zoom = z; storlek(); },
        klar() { for (const d of delar.values()) { const m = d.mesh, mal = d.mal; m.position.set(mal.x, mal.y, mal.z); m.scale.set(mal.b, mal.h, mal.d); } },
        stoppa() { igang = false; obs.disconnect(); renderer.dispose(); behallare.removeChild(dom); behallare.removeChild(skyltlager); },
    };
}
