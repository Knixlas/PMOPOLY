/**
 * PMOPOLY - Phase 4 (Förvaltning 2.0) renderer.
 *
 * Designdoks-anpassningar:
 *  - FC/FS-arketyper utan lön/kostnad
 *  - Yield-kö (3 framåt) synlig
 *  - Live slutresultat i status-rutan
 *  - Margin call visas tydligt på fastigheter
 *  - Mittenrutan visar fastighet med dess kort istället för spelplanen
 */
import { sendAction } from './app.js';
import { showPreview, previewStaff, previewMarketBuy } from './components.js';

export function renderPhase4Action(panel, gs, pending) {
    const action = pending.action;
    const me = gs.players.find(p => p.id === pending.player_id);
    const statusHtml = me ? renderF4Status(me, gs) : '';

    switch (action) {
        case 'f4_hire':
            renderHireStaff(panel, pending, statusHtml);
            break;
        case 'f4_energy_upgrade':
            renderEnergyUpgrade(panel, pending, statusHtml, me);
            break;
        case 'f4_market':
            renderMarket(panel, pending, statusHtml);
            break;
        case 'f4_market_sell':
            renderMarketSell(panel, pending, statusHtml);
            break;
        case 'f4_market_buy':
            renderMarketBuy(panel, pending, statusHtml);
            break;
        case 'continue':
            renderContinue(panel, pending, statusHtml, gs);
            break;
        default:
            panel.innerHTML = statusHtml + `<h3>Skede 3</h3><p>${pending.message || ''}</p>`;
    }
}

// ── Status-ruta ────────────────────────────────────────────────────────────
// Visar FC/FS, fastighetsantal, EK, restkort, yield-kö, live slutpoäng.

function renderF4Status(player, gs) {
    const staff = player.staff || [];
    const fc = staff.find(s => s.roll === 'FC');
    const fs = staff.find(s => s.roll === 'FS');
    const fastigheter = player.fastigheter || [];
    const marginCalls = (player.f4_margin_call_props || []).length;

    const live = (gs.f4_live_scores || {})[player.id] || null;
    const live_html = live ? `
        <div class="f4-live-score" style="margin-top:8px;padding:6px 8px;background:rgba(0,0,0,0.05);border-radius:4px;font-size:0.85em;">
            <strong>Slutresultat just nu:</strong>
            S1 <strong>${live.skede1}</strong> + S2 <strong>${live.skede2}</strong> + S3 <strong>${live.skede3}</strong>
            = ${live.rapong} × f(n) ${live.f_n} = <strong style="color:var(--burgundy)">${live.score} poäng</strong>
        </div>` : '';

    const yieldQueueHtml = renderYieldQueue(gs);

    const fc_text = fc ? `FC: <strong>${fc.namn}</strong>` : '<em style="color:#c00">FC saknas</em>';
    const fs_text = fs ? `FS: <strong>${fs.namn}</strong>` : '<em style="color:#c00">FS saknas</em>';

    return `
        <div class="gf-status">
            <div class="gf-stats">
                <span class="pstat">Fast: ${fastigheter.length}${marginCalls > 0 ? ` <span style="color:#c00">⚠ ${marginCalls} margin call</span>` : ''}</span>
                <span class="pstat">EK: ${player.eget_kapital} Mkr</span>
                <span class="pstat">Restkort: ${player.f4_restkort || 0}/3</span>
                <span class="pstat">${fc_text}</span>
                <span class="pstat">${fs_text}</span>
            </div>
            ${yieldQueueHtml}
            ${live_html}
        </div>
    `;
}

function renderYieldQueue(gs) {
    const qb = gs.f4_yield_queue_bostader || [];
    const qk = gs.f4_yield_queue_kommersiellt || [];
    if (qb.length === 0 && qk.length === 0) return '';
    const fmt = v => (v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1)) + ' pp';
    const cells = (arr) => arr.length === 0
        ? '<span class="muted">–</span>'
        : arr.map(v => `<span class="yield-cell ${v < 0 ? 'down' : v > 0 ? 'up' : ''}">${fmt(v)}</span>`).join(' ');
    return `
        <div class="yield-queue" style="margin-top:6px;font-size:0.8em;">
            <div>Yield bostäder nu <strong>${gs.f4_yield_b}%</strong> · kommande: ${cells(qb)}</div>
            <div>Yield kommersiellt nu <strong>${gs.f4_yield_k}%</strong> · kommande: ${cells(qk)}</div>
        </div>
    `;
}

// ── Anställ FC + FS (utan lön/kostnad) ────────────────────────────────────

function renderHireStaff(panel, pending, statusHtml) {
    const available = pending.available || [];
    const mustHire = pending.must_hire;
    const hasFc = pending.has_fc;
    const hasFs = pending.has_fs;

    let html = statusHtml;
    html += `<h3>Anställ personal</h3>`;
    html += `<div class="planning-status">
        <div class="progress-text">
            ${hasFc ? '✓' : '○'} Fastighetschef (FC) ·
            ${hasFs ? '✓' : '○'} Fastighetsspecialist (FS)
        </div>
        <div class="sub-text" style="font-size:0.85em;color:#666">
            Båda måste anställas. Inga lönekostnader — varje arketyp har egenskaper som påverkar spelet på fastighetsnivå.
        </div>
    </div>`;

    // Gruppera per roll
    const fcs = available.filter(s => s.roll === 'FC');
    const fss = available.filter(s => s.roll === 'FS');

    const renderCard = (s) => `
        <div class="supplier-option f4-staff-card" data-id="${s.id}">
            <div class="sup-header">
                <span class="sup-name">[${s.roll}] ${s.namn}</span>
            </div>
            <div class="sup-stats">${s.specialisering}</div>
        </div>
    `;

    if (!hasFc && fcs.length > 0) {
        html += `<h4 style="margin-top:12px">Fastighetschefer (välj en):</h4>`;
        fcs.forEach(s => html += renderCard(s));
    }
    if (!hasFs && fss.length > 0) {
        html += `<h4 style="margin-top:12px">Fastighetsspecialister (välj en):</h4>`;
        fss.forEach(s => html += renderCard(s));
    }

    if (!mustHire) {
        html += `<button class="btn btn-secondary" id="f4-hire-done" style="margin-top:12px">Klar med anställning</button>`;
    }

    panel.innerHTML = html;

    panel.querySelectorAll('.f4-staff-card').forEach(el => {
        el.addEventListener('click', () => {
            const s = available.find(st => st.id === el.dataset.id);
            if (s) {
                showPreview(previewStaff(s), () => {
                    sendAction({ action: 'f4_hire', value: el.dataset.id });
                });
            }
        });
    });

    const doneBtn = document.getElementById('f4-hire-done');
    if (doneBtn) {
        doneBtn.addEventListener('click', () => {
            sendAction({ action: 'f4_hire', value: null });
        });
    }
}

// ── Energiuppgradering med garanti-token ───────────────────────────────────

function renderEnergyUpgrade(panel, pending, statusHtml, me) {
    const upgradeable = pending.upgradeable || [];
    const garantier = (me && me.f4_energi_garanti) || {};
    let html = statusHtml;
    html += `<h3>${pending.message || 'Energiuppgradering'}</h3>`;
    html += `<p class="sub-text">EK: ${pending.eget_kapital} Mkr · D20 ≥ 10 för success (kostnaden dras även vid fail, men nästa försök på samma fastighet blir auto-success)</p>`;

    if (upgradeable.length === 0) {
        html += `<p class="muted">Alla fastigheter har redan energiklass A!</p>`;
    } else {
        upgradeable.forEach(u => {
            const canAfford = u.cost <= pending.eget_kapital;
            const har_garanti = (garantier[u.namn] || 0) > 0;
            html += `
                <div class="supplier-option ${!canAfford ? 'blocked' : ''}" data-namn="${u.namn}">
                    <div class="sup-header">
                        <span class="sup-name">${u.namn} (${u.typ})</span>
                        <span class="sup-cost">${u.ek} → ${u.new_ek} | ${u.cost} Mkr${har_garanti ? ' · 🎯 GARANTI' : ''}</span>
                    </div>
                    ${har_garanti ? '<div style="color:#0a7;font-size:0.85em">Nästa försök lyckas automatiskt (sparade tokens: ' + garantier[u.namn] + ')</div>' : ''}
                    ${!canAfford ? '<div class="sup-blocked">Inte råd</div>' : ''}
                </div>
            `;
        });
    }

    html += `<button class="btn btn-secondary" id="f4-energy-skip">Hoppa över</button>`;
    panel.innerHTML = html;

    panel.querySelectorAll('.supplier-option:not(.blocked)').forEach(el => {
        el.addEventListener('click', () => {
            sendAction({ action: 'f4_energy_upgrade', value: el.dataset.namn });
        });
    });

    document.getElementById('f4-energy-skip').addEventListener('click', () => {
        sendAction({ action: 'f4_energy_upgrade', value: null });
    });
}

// ── Marknad ────────────────────────────────────────────────────────────────

function renderMarket(panel, pending, statusHtml) {
    let html = statusHtml;
    html += `<h3>Fastighetsmarknad</h3>`;
    html += `<p class="sub-text">Verkligt EK: ${pending.real_ek} Mkr</p>`;

    const buyList = pending.buy_list || [];
    if (buyList.length > 0) {
        html += `<h4>Till salu:</h4>`;
        buyList.forEach(b => {
            html += `<div class="f4-market-info">
                ${b.namn} (${b.typ}) BTA:${b.bta} | DN:${b.driftnetto}/kv | EK:${b.ek} |
                Pris: ${b.cost_30} Mkr ${!b.can_afford ? '⛔' : ''}
            </div>`;
        });
    }

    html += `<div class="gf-buttons">`;
    if (pending.sell_list && pending.sell_list.length > 1) {
        html += `<button class="btn btn-warning" id="f4-market-sell">Sälj</button>`;
    }
    if (pending.can_buy && buyList.some(b => b.can_afford)) {
        html += `<button class="btn btn-primary" id="f4-market-buy">Köp</button>`;
    }
    html += `<button class="btn btn-secondary" id="f4-market-skip">Hoppa över</button>`;
    html += `</div>`;

    panel.innerHTML = html;

    const sellBtn = document.getElementById('f4-market-sell');
    if (sellBtn) sellBtn.addEventListener('click', () => {
        sendAction({ action: 'f4_market', value: 'sell' });
    });
    const buyBtn = document.getElementById('f4-market-buy');
    if (buyBtn) buyBtn.addEventListener('click', () => {
        sendAction({ action: 'f4_market', value: 'buy' });
    });
    document.getElementById('f4-market-skip').addEventListener('click', () => {
        sendAction({ action: 'f4_market', value: 'skip' });
    });
}

function renderMarketSell(panel, pending, statusHtml) {
    let html = statusHtml;
    html += `<h3>${pending.message}</h3>`;
    html += `<p class="sub-text">Verkligt EK: ${pending.real_ek} Mkr</p>`;

    if (pending.forced) {
        html += `<div style="background:#fee;border:2px solid #c00;padding:10px;margin:8px 0;border-radius:4px">
            <strong style="color:#c00">⚠ TVÅNGSFÖRSÄLJNING</strong> — du måste sälja minst en fastighet
            (margin call: MV under lånebelopp).
        </div>`;
    }

    (pending.sell_list || []).forEach((s, i) => {
        html += `
            <div class="supplier-option" data-idx="${i}">
                <div class="sup-header">
                    <span class="sup-name">${s.namn} (${s.typ})</span>
                    <span class="sup-cost">FV: ${s.fv} | Du får: ${s.earn_30} Mkr</span>
                </div>
            </div>
        `;
    });

    if (!pending.forced) {
        html += `<button class="btn btn-secondary" id="f4-sell-skip">Avbryt</button>`;
    }

    panel.innerHTML = html;

    panel.querySelectorAll('.supplier-option').forEach(el => {
        el.addEventListener('click', () => {
            sendAction({ action: 'f4_market_sell', value: parseInt(el.dataset.idx) });
        });
    });

    const skipBtn = document.getElementById('f4-sell-skip');
    if (skipBtn) skipBtn.addEventListener('click', () => {
        sendAction({ action: 'f4_market_sell', value: null });
    });
}

function renderMarketBuy(panel, pending, statusHtml) {
    let html = statusHtml;
    html += `<h3>Köp fastighet</h3>`;
    html += `<p class="sub-text">Verkligt EK: ${pending.real_ek} Mkr</p>`;

    (pending.buy_list || []).forEach((b, i) => {
        html += `
            <div class="supplier-option ${!b.can_afford ? 'blocked' : ''}" data-idx="${i}">
                <div class="sup-header">
                    <span class="sup-name">${b.namn} (${b.typ})</span>
                    <span class="sup-cost">Pris: ${b.cost_30} Mkr</span>
                </div>
                <div class="sup-stats">BTA:${b.bta} | DN:${b.driftnetto}/kv | EK:${b.ek} | FV:${b.fv}</div>
                ${!b.can_afford ? '<div class="sup-blocked">Inte råd</div>' : ''}
            </div>
        `;
    });

    html += `<button class="btn btn-secondary" id="f4-buy-skip">Avbryt</button>`;
    panel.innerHTML = html;

    const buyList = pending.buy_list || [];
    panel.querySelectorAll('.supplier-option:not(.blocked)').forEach(el => {
        el.addEventListener('click', () => {
            const b = buyList[parseInt(el.dataset.idx)];
            if (b) {
                showPreview(previewMarketBuy(b), () => {
                    sendAction({ action: 'f4_market_buy', value: parseInt(el.dataset.idx) });
                });
            }
        });
    });

    document.getElementById('f4-buy-skip').addEventListener('click', () => {
        sendAction({ action: 'f4_market_buy', value: null });
    });
}

function renderContinue(panel, pending, statusHtml, gs) {
    let html = statusHtml;
    const sub = gs.sub_state || '';

    if (sub === 'f4_world_event' && pending.world_event) {
        const we = pending.world_event;
        html += `<div class="event-card-display">
            <div class="ec-name">🌍 ${we.rubrik}</div>
            <div class="ec-desc">${we.beskrivning}</div>
            <div class="ec-effect">${we.effekt_typ}: ${we.effekt_mkr} Mkr | Påverkar: ${we.poverkar}</div>
        </div>`;
        html += `<p class="sub-text">Q${pending.quarter} | Yield B: ${pending.yield_b}% K: ${pending.yield_k}%</p>`;
    } else if (sub === 'f4_rent_result') {
        const mod = pending.fc_modifier || 0;
        const modText = mod ? ` ${mod > 0 ? '+' : ''}${mod} FC-bonus` : '';
        html += `<div class="event-card-display">
            <div class="ec-name">Hyresförhandling</div>
            <div class="ec-roll">
                FC ${pending.fc_name} (${pending.fc_die}): ${pending.fc_roll} +
                FÄ: ${pending.fa_roll} −
                HGF: ${pending.hgf_roll}${modText} = <strong>${pending.netto}</strong>
            </div>
            <div class="ec-effect">Höjning: ${pending.hojning_per} Mkr × ${pending.hr_count} HR = ${pending.total} Mkr</div>
        </div>`;
    } else if (sub === 'f4_mgmt_events') {
        const results = pending.mgmt_results || [];
        if (results.length > 0) {
            html += `<h3>Händelsekort</h3>`;
            results.forEach(r => {
                const card = r.card || {};
                html += `<div class="f4-mgmt-result ${r.effect >= 0 ? 'positive' : 'negative'}">
                    <strong>${r.prop_namn}:</strong> ${card.rubrik || 'Inga kort'}
                    ${r.mitigated ? ` <em>(mildrad av ${r.mitigator})</em>` : ''}
                    <span class="f4-effect">${r.effect >= 0 ? '+' : ''}${r.effect} Mkr</span>
                </div>`;
            });
            html += `<p class="sub-text">EK: ${pending.eget_kapital} Mkr</p>`;
        } else {
            html += `<p class="muted">Inga händelsekort detta kvartal.</p>`;
        }
    } else {
        html += `<p>${pending.message || ''}</p>`;
        if (pending.effect) {
            html += `<div class="event-card-display"><div class="ec-effect">${pending.effect}</div></div>`;
        }
    }

    html += `<button class="btn btn-primary" id="f4-continue">Fortsätt</button>`;
    panel.innerHTML = html;

    document.getElementById('f4-continue').addEventListener('click', () => {
        sendAction({ action: 'continue' });
    });
}

// ── Mittenruta: fastigheter + deras kort (istället för spelplan) ──────────
// Exporteras och kallas från game.js när phase är phase4_forvaltning.

export function renderPhase4Board(boardElement, gs) {
    const me = gs.players.find(p => p.id === gs.current_player_id) || gs.players[0];
    if (!me) return;
    const fastigheter = me.fastigheter || [];
    const marginCallSet = new Set(me.f4_margin_call_props || []);
    const garantier = me.f4_energi_garanti || {};

    let html = '<div class="f4-board-fastigheter" style="padding:12px;max-width:100%">';
    html += `<h3 style="margin-top:0">Dina fastigheter (Q${gs.f4_quarter || 1}/4)</h3>`;

    if (fastigheter.length === 0) {
        html += '<p class="muted">Inga fastigheter att förvalta.</p>';
    } else {
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;">';
        fastigheter.forEach(f => {
            const ek = (me.projekt_energiklass || {})[f.namn] || f.energiklass || 'C';
            const isMarginCall = marginCallSet.has(f.namn);
            const har_garanti = (garantier[f.namn] || 0) > 0;
            const border = isMarginCall ? '3px solid #c00' : '1px solid var(--ink-line)';
            const bg = isMarginCall ? '#fee' : 'var(--card-bg, #fff)';
            html += `
                <div class="f4-prop-card" style="border:${border};background:${bg};border-radius:6px;padding:10px;">
                    <div style="display:flex;justify-content:space-between;align-items:start;">
                        <strong>${f.namn}</strong>
                        <span class="badge" style="background:${ekColor(ek)};color:white;padding:2px 8px;border-radius:10px;font-size:0.8em">EK ${ek}</span>
                    </div>
                    <div style="font-size:0.85em;color:#666;margin-top:2px">${f.typ}</div>
                    <div style="margin-top:6px;font-size:0.9em">
                        <div>Bas-DN: <strong>${f.bas_dn || '–'}</strong></div>
                        <div>Lån: <strong>${f.lanebelopp || 0} Mkr</strong> (ränta ${f.rantekostnad_kvartal || 0}/kv)</div>
                    </div>
                    ${isMarginCall ? '<div style="margin-top:6px;color:#c00;font-weight:bold">⚠ MARGIN CALL — fastigheten kan tvångsförsäljas</div>' : ''}
                    ${har_garanti ? `<div style="margin-top:6px;color:#0a7">🎯 Garanti: nästa energiuppgradering lyckas automatiskt</div>` : ''}
                </div>
            `;
        });
        html += '</div>';
    }
    html += '</div>';
    boardElement.innerHTML = html;
}

function ekColor(ek) {
    return { A: '#0a7', B: '#5a7', C: '#888', D: '#c87', E: '#c44' }[ek] || '#888';
}
