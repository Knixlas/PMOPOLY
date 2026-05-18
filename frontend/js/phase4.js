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

    html += `<button class="btn btn-secondary" id="f4-energy-skip">Gå till nästa steg</button>`;
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
    html += `<button class="btn btn-secondary" id="f4-market-skip">Gå till nästa steg</button>`;
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

// ── Mittenruta: börsliknande Skede 3-vy ──────────────────────────────────
// Yield-banner + live-poängtavla + yield-graf + fastigheter med kortrader.

const EK_TYP_FARG = {
    'BRF': '#7a3835', 'HYRESRÄTT': '#a23a45', 'FÖRSKOLA': '#3f4a1f',
    'LOKAL': '#7a5a1f', 'KONTOR': '#1f4d7a',
};

export function renderPhase4Board(boardElement, gs) {
    // Visa alltid den lokala spelarens fastigheter (inte aktiv spelares).
    // f4_live_scores är publika — alla ser allas siffror.
    const myId = (typeof window !== 'undefined' && window._state && window._state.playerId) || null;
    const me = (myId && gs.players.find(p => p.id === myId))
            || gs.players.find(p => p.id === gs.current_player_id)
            || gs.players[0];
    if (!me) return;

    let html = '<div class="f4-stockboard" style="padding:14px;font-family:system-ui,sans-serif;height:100%;overflow-y:auto;">';
    html += renderYieldBanner(gs);
    html += renderScoreboard(gs);
    html += renderYieldChart(gs);
    html += renderPersonkortHand(me);
    html += renderFastighetsPaneler(me);
    html += '</div>';
    // Säkerställ att board-containern kan scrolla — inga overflow-hidden eller
    // flex-centrering från SVG-läge som annars klipper bort innehåll.
    boardElement.style.overflow = 'auto';
    boardElement.style.height = '100%';
    boardElement.style.alignItems = 'stretch';
    boardElement.style.justifyContent = 'flex-start';
    boardElement.style.padding = '0';
    boardElement.innerHTML = html;
}

// Stora yield-siffror överst, med 3 framtida rörelser
function renderYieldBanner(gs) {
    const qb = gs.f4_yield_queue_bostader || [];
    const qk = gs.f4_yield_queue_kommersiellt || [];
    const fmt = v => `<span class="yield-cell ${v < 0 ? 'down' : v > 0 ? 'up' : ''}">${v > 0 ? '+' : ''}${v.toFixed(1)}</span>`;
    const cells = arr => arr.length ? arr.map(fmt).join(' ') : '<span class="muted">–</span>';
    return `
        <div class="f4-yield-banner" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:12px;">
            <div style="background:#1e3a5f;color:#fff;padding:12px 14px;border-radius:6px;">
                <div style="font-size:0.75em;letter-spacing:0.15em;opacity:0.7;text-transform:uppercase">Bostäder</div>
                <div style="font-size:1.8em;font-weight:700;line-height:1.1">${gs.f4_yield_b}%</div>
                <div style="font-size:0.78em;opacity:0.85;margin-top:4px">Kommande: ${cells(qb)}</div>
            </div>
            <div style="background:#5a3e1a;color:#fff;padding:12px 14px;border-radius:6px;">
                <div style="font-size:0.75em;letter-spacing:0.15em;opacity:0.7;text-transform:uppercase">Kommersiellt</div>
                <div style="font-size:1.8em;font-weight:700;line-height:1.1">${gs.f4_yield_k}%</div>
                <div style="font-size:0.78em;opacity:0.85;margin-top:4px">Kommande: ${cells(qk)}</div>
            </div>
        </div>
    `;
}

// Live slutpoäng som "börstavla" — alla spelare
function renderScoreboard(gs) {
    const scores = gs.f4_live_scores || {};
    const players = gs.players || [];
    if (players.length === 0) return '';

    const rows = players.map(p => {
        const s = scores[p.id] || { skede1: 0, skede2: 0, skede3: 0, score: 0, f_n: 1, total_dn: 0 };
        return `
            <tr>
                <td style="padding:5px 8px;font-weight:600;color:${p.color}">${p.name}</td>
                <td style="text-align:right;padding:5px 8px">${s.skede1}</td>
                <td style="text-align:right;padding:5px 8px">${s.skede2}</td>
                <td style="text-align:right;padding:5px 8px">${s.skede3}</td>
                <td style="text-align:right;padding:5px 8px;color:#666">${s.f_n}×</td>
                <td style="text-align:right;padding:5px 8px;font-weight:700;font-size:1.1em">${s.score}</td>
                <td style="text-align:right;padding:5px 8px;color:#666;font-size:0.85em">EK ${p.eget_kapital}</td>
                <td style="text-align:right;padding:5px 8px;color:#666;font-size:0.85em">DN ${s.total_dn}</td>
            </tr>`;
    }).join('');

    return `
        <div class="f4-scoreboard" style="margin-bottom:12px;background:#fafafa;border:1px solid #ddd;border-radius:6px;overflow:hidden;">
            <div style="background:#222;color:#fff;padding:6px 10px;font-size:0.85em;font-weight:600;letter-spacing:0.1em;text-transform:uppercase">
                Slutresultat just nu · Q${gs.f4_quarter || 1}/4
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:0.9em;">
                <thead style="background:#f0f0f0;font-size:0.8em;color:#666;">
                    <tr>
                        <th style="text-align:left;padding:4px 8px">Spelare</th>
                        <th style="text-align:right;padding:4px 8px">S1</th>
                        <th style="text-align:right;padding:4px 8px">S2</th>
                        <th style="text-align:right;padding:4px 8px">S3</th>
                        <th style="text-align:right;padding:4px 8px">f(n)</th>
                        <th style="text-align:right;padding:4px 8px">Poäng</th>
                        <th style="text-align:right;padding:4px 8px">EK</th>
                        <th style="text-align:right;padding:4px 8px">DN</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

// Enkel yield-utveckling som SVG-linje
function renderYieldChart(gs) {
    const history = gs.f4_history || [];
    if (history.length < 2) {
        return ''; // Visa bara när vi har minst 2 datapunkter
    }
    const w = 560, h = 110, padX = 30, padY = 14;
    const innerW = w - padX*2, innerH = h - padY*2;
    const xs = history.map((_, i) => padX + (i / (history.length - 1)) * innerW);
    const yMin = 2, yMax = 7;
    const yScale = v => padY + innerH - ((v - yMin) / (yMax - yMin)) * innerH;
    const pathFor = (key, color) => {
        const d = history.map((h, i) => `${i === 0 ? 'M' : 'L'} ${xs[i]} ${yScale(h[key])}`).join(' ');
        const dots = history.map((h, i) =>
            `<circle cx="${xs[i]}" cy="${yScale(h[key])}" r="2.5" fill="${color}"/>`
        ).join('');
        return `<path d="${d}" stroke="${color}" stroke-width="2" fill="none"/>${dots}`;
    };
    const labelX = history.map((h, i) =>
        `<text x="${xs[i]}" y="${h-2}" font-size="9" fill="#888" text-anchor="middle">Q${h.quarter}</text>`
    ).join('');
    const gridY = [3, 4, 5, 6].map(v =>
        `<line x1="${padX}" y1="${yScale(v)}" x2="${w - padX}" y2="${yScale(v)}" stroke="#eee" stroke-width="1"/>
         <text x="${padX-4}" y="${yScale(v)+3}" font-size="9" fill="#888" text-anchor="end">${v}%</text>`
    ).join('');
    return `
        <div class="f4-yieldchart" style="margin-bottom:12px;background:#fafafa;border:1px solid #ddd;border-radius:6px;padding:8px 10px;">
            <div style="font-size:0.78em;color:#666;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">
                Yield-utveckling · <span style="color:#1e3a5f">━ Bostäder</span> · <span style="color:#5a3e1a">━ Kommersiellt</span>
            </div>
            <svg viewBox="0 0 ${w} ${h}" style="width:100%;height:${h}px">
                ${gridY}
                ${pathFor('yield_b', '#1e3a5f')}
                ${pathFor('yield_k', '#5a3e1a')}
                ${labelX}
            </svg>
        </div>
    `;
}

// Energiklass → DN-modifier (matchar backend EK_DN_MODIFIER)
const EK_DN_MOD = { A: 2, B: 1, C: 0, D: -1, E: -2 };

// Fastigheter i centrum — varje fastighet är en panel med rader under för kort
function renderFastighetsPaneler(me) {
    const fastigheter = me.fastigheter || [];
    const marginCallSet = new Set(me.f4_margin_call_props || []);
    const garantier = me.f4_energi_garanti || {};
    const ekMap = me.projekt_energiklass || {};
    const dnBonus = me.driftnetto_bonus || {};

    if (fastigheter.length === 0) {
        return '<div class="muted" style="text-align:center;padding:20px">Inga fastigheter att förvalta.</div>';
    }

    const handelseMap = me.f4_handelse_per_prop || {};

    const cards = fastigheter.map(f => {
        const ek = ekMap[f.namn] || f.energiklass || 'C';
        const ekMod = EK_DN_MOD[ek] || 0;
        const bas = f.bas_dn || 0;
        const synligDn = Math.max(0, bas + ekMod);   // bas + EK-modifier
        const doltDn = Math.round(dnBonus[f.namn] || 0);
        const totalDn = synligDn + doltDn;
        const isMarginCall = marginCallSet.has(f.namn);
        const har_garanti = (garantier[f.namn] || 0) > 0;
        const typFarg = EK_TYP_FARG[f.typ] || '#444';
        const border = isMarginCall ? '3px solid #c00' : '1px solid #ccc';

        // Räkna kort per kategori per fastighet
        const handelser = handelseMap[f.namn] || [];
        const plusCount = handelser.filter(h => h.effekt === 'pluskort').length;
        const minusCount = handelser.filter(h => h.effekt === 'minuskort').length;
        const varnCount = handelser.filter(h => h.effekt === 'varning').length;
        const energiVarnCount = handelser.filter(h => h.effekt === 'energivarning').length;

        const cardRow = (label, count, threshold, color) => {
            const filled = count > 0;
            const triggered = count >= threshold;
            const bg = triggered ? color + '33' : filled ? color + '22' : '#f5f5f5';
            const fg = filled ? color : '#aaa';
            const border = triggered ? `2px solid ${color}` : `1px ${filled ? 'solid' : 'dashed'} ${filled ? color + '88' : '#ddd'}`;
            return `<div style="background:${bg};padding:3px 5px;border-radius:3px;text-align:center;color:${fg};border:${border};font-weight:${filled?'600':'400'}">${label} ${count}/${threshold}</div>`;
        };

        const cardRows = `
            <div class="prop-cardrows" style="margin-top:8px;display:grid;grid-template-columns:repeat(4,1fr);gap:4px;font-size:0.7em;">
                ${cardRow('+ Plus', plusCount, 3, '#1F5E2B')}
                ${cardRow('− Minus', minusCount, 3, '#7A2020')}
                ${cardRow('⚠ Varning', varnCount, 3, '#7A5A1F')}
                ${cardRow('⚡ Energi', energiVarnCount, 3, '#7A6E1F')}
            </div>
        `;

        // DN-rad: stor synlig + liten dold
        const dnRow = `
            <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:4px">
                <span style="color:#888;font-size:0.78em">DN</span>
                <span style="font-weight:700;font-size:1.3em">${synligDn}</span>
                <span style="color:#666;font-size:0.78em">synlig (bas ${bas} ${ekMod >= 0 ? '+' : ''}${ekMod} EK)</span>
                ${doltDn ? `<span style="color:#a06;font-size:0.85em;font-weight:600">+ ${doltDn} dolt</span>` : '<span style="color:#bbb;font-size:0.78em">+ 0 dolt</span>'}
            </div>
        `;

        return `
            <div class="f4-prop-card" style="border:${border};border-radius:6px;background:#fff;overflow:hidden;${isMarginCall ? 'box-shadow:0 0 0 1px #c00 inset;' : ''}">
                <div style="background:${typFarg};color:#fff;padding:8px 10px;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-weight:700">${f.namn}</div>
                        <div style="font-size:0.72em;opacity:0.85">${f.typ}</div>
                    </div>
                    <span class="ek-badge" style="background:${ekColor(ek)};color:#fff;padding:3px 9px;border-radius:11px;font-size:0.8em;font-weight:600">EK ${ek}</span>
                </div>
                <div style="padding:8px 10px;">
                    ${dnRow}
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.85em;">
                        <div><div style="color:#888;font-size:0.78em">Lån</div><div style="font-weight:600">${f.lanebelopp || 0} Mkr</div></div>
                        <div><div style="color:#888;font-size:0.78em">Ränta/kv</div><div style="font-weight:600">${f.rantekostnad_kvartal || 0}</div></div>
                    </div>
                    ${isMarginCall ? '<div style="margin-top:8px;background:#fee;border:1px solid #c00;color:#c00;padding:5px 8px;border-radius:4px;font-size:0.85em;font-weight:600">⚠ MV<lån nästa kvartal — tvångsförsäljs vid marknadsfasen</div>' : ''}
                    ${har_garanti ? `<div style="margin-top:8px;background:#efe;border:1px solid #0a7;color:#0a7;padding:5px 8px;border-radius:4px;font-size:0.85em">🎯 Energi-garanti (×${garantier[f.namn]}): nästa uppgradering lyckas automatiskt</div>` : ''}
                    ${cardRows}
                </div>
            </div>
        `;
    }).join('');

    return `
        <div class="f4-fastigheter" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
            ${cards}
        </div>
    `;
}

function ekColor(ek) {
    return { A: '#0a7', B: '#5a7', C: '#888', D: '#c87', E: '#c44' }[ek] || '#888';
}

// Personkort på hand (FC + FS)
function renderPersonkortHand(me) {
    const hand = me.f4_personkort_hand || [];
    if (hand.length === 0) {
        return ''; // visa inget om handen är tom
    }
    const cards = hand.map(k => {
        const rollColor = k.roll === 'FC' ? '#7A2020' : '#1F4D7A';
        return `
            <div class="f4-personkort" style="background:${rollColor};color:#fff;padding:8px 10px;border-radius:6px;min-width:160px;flex:0 0 auto;">
                <div style="font-size:0.7em;opacity:0.7;text-transform:uppercase;letter-spacing:0.1em">${k.roll}-kort</div>
                <div style="font-weight:700;margin-top:2px">${k.rubrik}</div>
                <div style="font-size:0.78em;opacity:0.85;margin-top:3px">${k.beskrivning || ''}</div>
            </div>`;
    }).join('');
    return `
        <div class="f4-hand" style="margin-bottom:12px;background:#fafafa;border:1px solid #ddd;border-radius:6px;padding:8px 10px;">
            <div style="font-size:0.78em;color:#666;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">
                Personkort på hand · ${hand.length}/6
            </div>
            <div style="display:flex;gap:8px;overflow-x:auto">${cards}</div>
        </div>
    `;
}
